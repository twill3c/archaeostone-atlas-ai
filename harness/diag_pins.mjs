// 地図の標の位置を実測する診断器(検品が落ちた原因の切り分け用)。
//
// 「重なっているらしい」で終わらせず、**画面座標を測って表にする**。
// 目視で見つけた欠陥は、直す前に矩形で実測する(HC-194)。
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { chromium } from "playwright";

const ROOT = new URL("../out/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
};

const server = createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p.endsWith("/")) p += "index.html";
    const file = join(ROOT, normalize(p).replace(/^[/\\]+/, ""));
    const body = await readFile(file);
    res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404).end("not found");
  }
});

await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;

const NEAR_PX = 30;

async function dump(page, label) {
  const info = await page.evaluate((nearPx) => {
    const pins = [...document.querySelectorAll(".map-pin")].map((el) => {
      const r = el.getBoundingClientRect();
      return {
        title: el.title.slice(0, 30),
        kind: el.className.includes("cluster") ? "群" : "単",
        x: Math.round(r.x + r.width / 2),
        y: Math.round(r.y + r.height / 2),
        w: Math.round(r.width),
      };
    });
    const near = [];
    for (let i = 0; i < pins.length; i += 1) {
      for (let j = i + 1; j < pins.length; j += 1) {
        const d = Math.hypot(pins[i].x - pins[j].x, pins[i].y - pins[j].y);
        if (d < nearPx) {
          near.push(`${pins[i].title} / ${pins[j].title} = ${d.toFixed(1)}px`);
        }
      }
    }
    const map = window.__atlasMap;
    return { pins, near, zoom: map ? map.getZoom() : null };
  }, NEAR_PX);

  console.log(`\n=== ${label}: 標 ${info.pins.length} 個  zoom=${info.zoom}`);
  for (const p of info.pins) {
    console.log(`   [${p.kind}] ${p.title.padEnd(32)} (${p.x},${p.y}) w=${p.w}`);
  }
  console.log(
    `   ${NEAR_PX}px 以内の組: ` + (info.near.length ? "\n     " + info.near.join("\n     ") : "無し"),
  );
  return info;
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push("console: " + m.text());
  });
  await page.route(/cyberjapandata|gbank\.gsj/, (route) => route.abort());
  await page.goto(base + "/map/", { waitUntil: "load" });

  // 標が出ないときは、まず「なぜ出ないか」を出す。
  try {
    await page.waitForSelector(".map-pin", { timeout: 15000 });
  } catch {
    const state = await page.evaluate(() => ({
      canvas: !!document.querySelector(".maplibregl-canvas"),
      markers: document.querySelectorAll(".maplibregl-marker").length,
      pins: document.querySelectorAll(".map-pin").length,
      mainText: document.querySelector("main")?.innerText.slice(0, 200) ?? null,
    }));
    console.log("標が出ない。状態:", JSON.stringify(state, null, 1));
    console.log("JS エラー:", errors.length ? errors : "無し");
    throw new Error("標が出ないので診断を打ち切る");
  }
  await dump(page, "初期ズーム");
  if (errors.length) console.log("JS エラー:", errors);

  const clusters = await page.locator(".map-pin--cluster").count();
  console.log(`\n群の数: ${clusters}`);

  if (clusters > 0) {
    await page.locator(".map-pin--cluster").first().click();
    await page.waitForTimeout(2500);
    await dump(page, "群を押した後");
  }
} finally {
  await browser.close();
  server.close();
}
