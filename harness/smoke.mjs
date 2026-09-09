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

await stat(join(ROOT, "index.html")).catch(() => {
  console.error("out/ が無い。先に `npm run build` を実行すること");
  process.exit(2);
});

await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;

const failures = [];
const check = (ok, msg) => {
  if (!ok) failures.push(msg);
};

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
  server.close();
}

if (failures.length) {
  console.error(`検品 失敗 ${failures.length} 件:`);
  for (const f of failures) console.error("  - " + f);
  process.exit(1);
}
console.log(
  `検品 OK — ${PAGES.length} 頁 x ${WIDTHS.length} 幅 + 地図の標・落ちた主張・権利表示・陽性対照`,
);
