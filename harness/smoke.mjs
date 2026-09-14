// 出荷物を実ブラウザで検品する(SPEC §7 G-11 / G-12 / G-14)。
//
// 静的検査では見つからない型の欠陥 —— 横溢れ・縦の伸びすぎ・図の内側の切れ・
// クライアント側の描画 —— を、実際に描画して確かめる。
// out/ を素の静的サーバで配り、chromium で開く。
//
// 検品器自身が壊れていないかも疑う(HC-080)。だから
//   * 検品器は**振る舞い**で書く(要素名や実装の経路に依存させない)
//   * 陽性対照を最後に置き、検品器が実際に異常を捕まえられることを確かめる
//   * 失敗は必ず終了コードで知らせる(パイプの先で $? がすり替わらないように)
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { chromium } from "playwright";
import { computeStamp } from "../scripts/build_stamp.mjs";
import { gzipSync } from "node:zlib";

// N-01 の上限(gzip)。
const INITIAL_LOAD_LIMIT = 3 * 1024 * 1024;
const loads = [];

const ROOT = new URL("../out/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");

// 見るのは一つの幅ではない(HC-078)。
const WIDTHS = [320, 390, 768, 1280];
const PAGES = [
  "/",
  "/map/",
  "/sources/",
  "/geology/",
  "/jade/",
  "/documents/",
  "/ai-lab/",
  "/methodology/",
  "/licenses/",
];

// 縦の伸びすぎは列の潰れによく出る代理指標(HC-078)。
const MAX_PAGE_HEIGHT = 16000;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
};

const server = createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p.endsWith("/")) p += "index.html";
    const file = join(ROOT, normalize(p).replace(/^([/\\])+/, ""));
    const body = await readFile(file);
    res.writeHead(200, {
      "content-type": MIME[extname(file)] ?? "application/octet-stream",
    });
    res.end(body);
  } catch {
    res.writeHead(404).end("not found");
  }
});

// 本番検品: SMOKE_BASE_URL を与えると out/ を配らず、その URL を検品する。
const REMOTE = process.env.SMOKE_BASE_URL?.replace(/\/+$/, "") ?? null;

let base;
if (REMOTE) {
  base = REMOTE;
} else {
  await stat(join(ROOT, "index.html")).catch(() => {
    console.error("out/ が無い。先に `npm run build` を実行すること");
    process.exit(2);
  });
  await new Promise((r) => server.listen(0, r));
  base = `http://127.0.0.1:${server.address().port}`;
}

const failures = [];
const check = (ok, msg) => {
  if (!ok) failures.push(msg);
};

// ── 刻印: 配られているものが手元と同じか(T-415 / HC-148) ──
//
// 以下の検品は「健やかか」しか答えない。古い本番も健やかなので、
// **刻印が手元の木から計算した値と違えば、それだけで不合格にする。**
const expectedStamp = computeStamp().stamp;
{
  let served = null;
  try {
    const res = await fetch(`${base}/build-stamp.json`, { cache: "no-store" });
    if (res.ok) served = (await res.json()).stamp ?? null;
  } catch {
    served = null;
  }
  check(
    served === expectedStamp,
    `刻印が一致しない: 配信 ${served} / 手元 ${expectedStamp}(古い配布を検品している疑い)`,
  );
}

// 外部タイル(地理院・GSJ)は検品では取らない。ネットワークに依存させると
// 「取得に失敗した画面を検品して緑になる」型の偽の正常を作る。
const EXTERNAL_TILE = /cyberjapandata\.gsi\.go\.jp|gbank\.gsj\.jp/;

const browser = await chromium.launch();
try {
  for (const path of PAGES) {
    for (const width of WIDTHS) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      await page.route(EXTERNAL_TILE, (route) => route.abort());

      const res = await page.goto(base + path, { waitUntil: "load" });
      check(res?.status() === 200, `${path} @${width}: HTTP ${res?.status()}`);

      // 横溢れ(G-14)
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      check(overflow <= 1, `${path} @${width}: 横溢れ ${overflow}px`);

      // 縦の伸びすぎ(列の潰れの代理指標)
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
      check(
        height <= MAX_PAGE_HEIGHT,
        `${path} @${width}: 縦 ${height}px が上限 ${MAX_PAGE_HEIGHT}px を超えた(表の潰れを疑う)`,
      );

      // 出典表示が常時アクセス可能であること(構想書 §36)。
      // **要素名ではなく「出典の文が出ているか」で見る**(振る舞いで書く)。
      const attribution = await page.evaluate(() => {
        const text = document.body.innerText;
        return {
          hasGsi: text.includes("国土地理院"),
          hasGsj: text.includes("産総研地質調査総合センター"),
          hasNabunken: text.includes("奈良文化財研究所"),
        };
      });
      check(attribution.hasGsi, `${path} @${width}: 地理院の出典表示が無い`);
      check(attribution.hasGsj, `${path} @${width}: 産総研の出典表示が無い`);
      check(attribution.hasNabunken, `${path} @${width}: 奈良文化財研究所の出典表示が無い`);

      // 図の中の要素が viewBox に収まっているか(HC-159)。
      // ページの横溢れ検査は図の内側の切れを見ない。
      const clipped = await page.evaluate(() => {
        const out = [];
        for (const svg of document.querySelectorAll("svg[viewBox]")) {
          const vb = svg.viewBox.baseVal;
          const label = svg.getAttribute("aria-label") ?? svg.getAttribute("class") ?? "svg";
          for (const el of svg.querySelectorAll("text, rect, path, line, circle, polyline")) {
            let b;
            try {
              b = el.getBBox();
            } catch {
              continue;
            }
            if (b.width === 0 && b.height === 0) continue;
            const over = [];
            if (b.x < vb.x - 0.5) over.push(`左 ${(vb.x - b.x).toFixed(1)}`);
            if (b.y < vb.y - 0.5) over.push(`上 ${(vb.y - b.y).toFixed(1)}`);
            if (b.x + b.width > vb.x + vb.width + 0.5)
              over.push(`右 ${(b.x + b.width - vb.x - vb.width).toFixed(1)}`);
            if (b.y + b.height > vb.y + vb.height + 0.5)
              over.push(`下 ${(b.y + b.height - vb.y - vb.height).toFixed(1)}`);
            if (over.length) {
              out.push(
                `${label} の <${el.tagName}> ${JSON.stringify(
                  (el.textContent ?? "").trim().slice(0, 18),
                )} が ${over.join("・")} にはみ出す`,
              );
            }
          }
        }
        return out;
      });
      for (const c of clipped.slice(0, 4)) check(false, `${path} @${width}: ${c}`);

      // フリート共通フッタ(T-406/T-407)。**要素名ではなく中身で選ぶ**(App Menu を含む footer)。
      // 固定フッタは狭い幅で折り返して高くなり、逃げが足りないと本文の末尾を隠す ——
      // 横溢れの検査はそれを捕まえないので、幅ごとに実高と逃げを比べる。
      const fleet = await page.evaluate(() => {
        const f = [...document.querySelectorAll("footer")].find((el) =>
          el.innerText.includes("App Menu"),
        );
        if (!f) return null;
        const text = f.innerText;
        return {
          position: getComputedStyle(f).position,
          height: f.getBoundingClientRect().height,
          escape: parseFloat(getComputedStyle(document.body).paddingBottom),
          order: ["MIT License", "© 2026 坂田哲朗", "GitHub", "石材アトラスの歩き方", "石材アトラスの設計図", "App Menu"].map(
            (s) => text.indexOf(s),
          ),
          separators: (text.match(/・/g) ?? []).length,
        };
      });
      check(fleet !== null, `${path} @${width}: フリート共通フッタが無い`);
      if (fleet) {
        check(fleet.position === "fixed", `${path} @${width}: フッタが下部固定でない(${fleet.position})`);
        check(
          fleet.height <= fleet.escape,
          `${path} @${width}: フッタの実高 ${fleet.height.toFixed(0)}px が逃げ ${fleet.escape.toFixed(0)}px を超え、本文の末尾を隠す`,
        );
        const sorted = fleet.order.every((v, i, a) => v >= 0 && (i === 0 || v > a[i - 1]));
        check(sorted, `${path} @${width}: フッタの項目の並びが規約と違う ${JSON.stringify(fleet.order)}`);
        check(fleet.separators === 4, `${path} @${width}: 区切りが ${fleet.separators} 個(規約は 4 個)`);
      }

      check(errors.length === 0, `${path} @${width}: JS エラー ${errors[0] ?? ""}`);
      await page.close();
    }
  }

  // ── 地図の標が実際に置かれること ────────────────────
  //
  // 底図タイルは遮ってあるので、標が出るのは**データが読めているから**である。
  // 要素の数は名前ではなく親の子の総数で数える(HC-080)。
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route(EXTERNAL_TILE, (route) => route.abort());
    await page.goto(base + "/map/", { waitUntil: "load" });

    await page.waitForSelector(".map-pin", { timeout: 15000 });

    // 幾何の検査(HC-138)。**この検査は実際に壊れていた性質を測る。**
    // 実測(2026-09-09)では初期ズームで 5 件が重なり、互いのクリックを遮って
    // 押せなくなっていた。要素数の検査も「同一座標か」の検査も、それを捕まえない ——
    // 中心が丸めて一致しないだけで、重なっているからである。
    const PIN_PX = 15;
    const geometry = await page.evaluate((pinPx) => {
      const centres = [...document.querySelectorAll(".map-pin")].map((el) => {
        const r = el.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      });
      let tooClose = 0;
      let closest = Infinity;
      for (let i = 0; i < centres.length; i += 1) {
        for (let j = i + 1; j < centres.length; j += 1) {
          const d = Math.hypot(centres[i].x - centres[j].x, centres[i].y - centres[j].y);
          closest = Math.min(closest, d);
          if (d < pinPx) tooClose += 1;
        }
      }
      const xs = centres.map((c) => c.x);
      const ys = centres.map((c) => c.y);
      return {
        count: centres.length,
        tooClose,
        closest: Number.isFinite(closest) ? Math.round(closest) : null,
        spreadX: Math.round(Math.max(...xs) - Math.min(...xs)),
        spreadY: Math.round(Math.max(...ys) - Math.min(...ys)),
      };
    }, PIN_PX);

    check(geometry.count >= 5, `地図の標が ${geometry.count} 個しかない`);
    check(
      geometry.tooClose === 0,
      `標が ${PIN_PX}px 以内に重なっている: ${geometry.tooClose} 組(最近 ${geometry.closest}px)。互いのクリックを遮る`,
    );
    check(
      geometry.spreadX > 100 && geometry.spreadY > 100,
      `標が一点に固まっている(広がり ${geometry.spreadX}x${geometry.spreadY}px)`,
    );

    // 初期ズームでは群があるはず(近接した原産地が実在するので)。
    const clusters = await page.locator(".map-pin--cluster").count();
    check(clusters >= 1, "初期ズームで群が一つも無い(近接する原産地はまとめるはず)");

    // 群を押すと寄る。**操作が届いた証拠**としてズームの変化を見る(HC-138)。
    if (clusters >= 1) {
      const before = await page.evaluate(() => window.__mapZoomProbe ?? null);
      const cluster = page.locator(".map-pin--cluster").first();
      await cluster.scrollIntoViewIfNeeded();
      const singlesBefore = await page.locator(".map-pin--point, .map-pin--area").count();
      await cluster.click();
      await page.waitForFunction(
        (n) => document.querySelectorAll(".map-pin--point, .map-pin--area").length > n,
        singlesBefore,
        { timeout: 8000 },
      );
      const singlesAfter = await page.locator(".map-pin--point, .map-pin--area").count();
      check(
        singlesAfter > singlesBefore,
        `群を押しても単独の標が増えない(${singlesBefore} → ${singlesAfter})`,
      );
      void before;
    }

    // 単独の標を押すと Stone Passport が出て、座標の出所が読めること。
    const single = page.locator(".map-pin--point, .map-pin--area").first();
    await single.scrollIntoViewIfNeeded();
    await single.click();
    await page.waitForSelector(".passport", { timeout: 8000 });
    const passport = await page.locator(".passport").innerText();
    check(passport.includes("座標の出所"), "Stone Passport に座標の出所が無い");
    check(passport.includes("番目"), "Stone Passport に候補番号が無い");
    check(passport.includes("規則"), "Stone Passport に選んだ規則が無い");
    // F-07: 当該市町村の文献。市町村が決まらない原産地でも欄は出る(理由を書く)。
    check(passport.includes("当該市町村の文献"), "Stone Passport に当該市町村の文献が無い");
    check(
      /報告書|陸上と判定しない/.test(passport),
      "当該市町村の文献の欄に件数も理由も出ていない",
    );

    // F-06: 県別ヒスイ集計の層。既定では出さず、切り替えると 9 県の札と表が出る。
    check((await page.locator(".map-chip--jade").count()) === 0, "ヒスイ集計の札が既定で出ている");
    await page.locator("#layer-jade").check();
    await page.waitForSelector(".map-chip--jade", { timeout: 8000 });
    const chips = await page.locator(".map-chip--jade").count();
    check(chips === 9, `ヒスイ集計の札が ${chips} 個(集成表は 9 県)`);
    const controls = await page.locator(".atlas-map__controls").innerText();
    check(controls.includes("出土地点ではない"), "札の位置が出土地点ではないことが書かれていない");
    check(controls.includes("不明"), "点数の記録が無い県を「不明」と書いていない");
    await page.close();
  }

  // ── N-01: 初期ロード(gzip 換算)────────────────────────
  //
  // 同じ配信元から読まれたものを全部集め、本文を gzip して足す。外部タイルは数えない
  // (遮ってある)。**0 件を「軽い」と読まない** —— 何も数えていなければ落とす(HC-080)。
  for (const path of PAGES) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route(EXTERNAL_TILE, (route) => route.abort());
    const bodies = [];
    page.on("response", (response) => {
      if (response.url().startsWith(base) && response.status() < 400) {
        bodies.push(response.body().catch(() => Buffer.alloc(0)));
      }
    });
    await page.goto(base + path, { waitUntil: "networkidle" });
    const buffers = await Promise.all(bodies);
    const gzipBytes = buffers.reduce((sum, buffer) => sum + gzipSync(buffer).length, 0);
    loads.push({ path, resources: buffers.length, gzipBytes });
    check(
      buffers.length >= 3 && gzipBytes > 10_000,
      `${path}: 初期ロードを数えられていない(${buffers.length} 件)`,
    );
    check(
      gzipBytes < INITIAL_LOAD_LIMIT,
      `${path}: 初期ロード ${gzipBytes} B が上限 3 MB を超えた(N-01)`,
    );
    await page.close();
  }

  // ── 落ちた主張が画面に出ていること ──────────────────
  //
  // 「成立しなかった」を隠さないことが本アトラスの主眼なので、
  // それが画面に出ていることを検査で固定する。
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route(EXTERNAL_TILE, (route) => route.abort());
    await page.goto(base + "/geology/", { waitUntil: "load" });
    const text = await page.locator("main").innerText();
    check(text.includes("成立しなかった主張"), "落ちた主張の節が無い");
    check(text.includes("不成立"), "不成立の判定が画面に出ていない");
    check(/p = 0\.0/.test(text), "p 値が画面に出ていない");
    await page.close();
  }

  // ── AI ラボ: 判定と No-Go が隠れずに出ていること ────
  //
  // モデル推定は「成立しなかった」「作らなかった」を出すことが主眼なので、
  // 判定の札と No-Go の表が画面にあることを固定する。
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route(EXTERNAL_TILE, (route) => route.abort());
    await page.goto(base + "/ai-lab/", { waitUntil: "load" });
    const text = await page.locator("main").innerText();
    check(text.includes("G-10"), "AI ラボに G-10 の判定が無い");
    check(/成立|不成立/.test(text), "AI ラボに判定の結果が出ていない");
    check(text.includes("確認にはならない"), "分類器が H の確認にならないことが書かれていない");
    check(text.includes("No-Go"), "蛍光X線の No-Go が出ていない");
    check(text.includes("判定不能"), "判定不能の引き金が隠れている");
    await page.close();
  }

  // ── 配れない源が理由ごと出ていること ────────────────
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route(EXTERNAL_TILE, (route) => route.abort());
    await page.goto(base + "/licenses/", { waitUntil: "load" });
    const text = await page.locator("main").innerText();
    check(text.includes("配れない源"), "配れない源の節が無い");
    check(text.includes("糸魚川"), "糸魚川市の権利表示が出ていない");
    check(text.includes("robots"), "robots による除外の説明が出ていない");
    await page.close();
  }

  // ── 陽性対照: この検品器が実際に異常を捕まえられること ──
  //
  // 「異常なし」を返したとき、それが「検査した」を意味するかを確かめる(HC-080)。
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route(EXTERNAL_TILE, (route) => route.abort());
    await page.goto(base + "/", { waitUntil: "load" });

    // わざと横に溢れる要素を入れて、溢れの検査が反応することを見る。
    const overflowBefore = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    await page.evaluate(() => {
      const bad = document.createElement("div");
      bad.id = "positive-control-overflow";
      bad.style.cssText = "width:5000px;height:4px;";
      document.body.append(bad);
    });
    const overflowAfter = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    check(
      overflowBefore <= 1 && overflowAfter > 1,
      `陽性対照が発火しない(溢れ ${overflowBefore} → ${overflowAfter})。溢れの検査は働いていない`,
    );
    await page.close();
  }
} finally {
  await browser.close();
  if (!REMOTE) server.close();
}

if (failures.length) {
  console.error(`検品 失敗 ${failures.length} 件:`);
  for (const f of failures) console.error("  - " + f);
  process.exit(1);
}
console.log("初期ロード(同じ配信元・gzip 換算):");
for (const load of loads) {
  console.log(`  ${load.path.padEnd(14)} ${String(load.resources).padStart(3)} 件 ${(load.gzipBytes / 1024).toFixed(1).padStart(8)} KB`);
}
console.log(
  `検品 OK — ${base} 刻印 ${expectedStamp} / ${PAGES.length} 頁 x ${WIDTHS.length} 幅 + 地図の標・ヒスイ集計・当該市町村の文献・落ちた主張・権利表示・初期ロード・陽性対照`,
);
