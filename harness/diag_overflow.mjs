// 横に溢れている要素を名指しする診断器。
//
// 「どこかが溢れている」で終わらせず、**矩形を測って犯人を出す**(HC-194)。
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

const targets = process.argv.slice(2);
const PAGES = targets.length ? targets : ["/sources/", "/licenses/", "/geology/"];
const WIDTH = 320;

const browser = await chromium.launch();
try {
  for (const path of PAGES) {
    const page = await browser.newPage({ viewport: { width: WIDTH, height: 900 } });
    await page.route(/cyberjapandata|gbank\.gsj/, (route) => route.abort());
    await page.goto(base + path, { waitUntil: "load" });

    const report = await page.evaluate((width) => {
      const docRight = document.documentElement.clientWidth;
      const offenders = [];
      for (const el of document.querySelectorAll("*")) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        const over = Math.round(r.right - docRight);
        if (over > 0) {
          offenders.push({
            over,
            tag: el.tagName.toLowerCase(),
            cls: (el.className || "").toString().slice(0, 48),
            w: Math.round(r.width),
            left: Math.round(r.left),
            text: (el.textContent || "").trim().slice(0, 40),
            depth: (() => {
              let d = 0;
              for (let p = el; p; p = p.parentElement) d += 1;
              return d;
            })(),
          });
        }
      }
      offenders.sort((a, b) => b.over - a.over || b.depth - a.depth);

      // 右端が画面内でも、中身が自分の幅を超えている要素は親を押し広げうる。
      const internal = [];
      for (const el of document.querySelectorAll("*")) {
        const extra = el.scrollWidth - el.clientWidth;
        if (extra > 0 && el.clientWidth > 0) {
          const cs = getComputedStyle(el);
          internal.push({
            extra,
            tag: el.tagName.toLowerCase(),
            cls: (el.className || "").toString().slice(0, 48),
            clientWidth: el.clientWidth,
            scrollWidth: el.scrollWidth,
            overflowX: cs.overflowX,
            text: (el.textContent || "").trim().slice(0, 40),
          });
        }
      }
      internal.sort((a, b) => b.extra - a.extra);

      return {
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: docRight,
        viewport: width,
        offenders: offenders.slice(0, 12),
        internal: internal.slice(0, 12),
      };
    }, WIDTH);

    console.log(
      `\n=== ${path} @${WIDTH}: scrollWidth ${report.scrollWidth} / clientWidth ${report.clientWidth} (溢れ ${report.scrollWidth - report.clientWidth}px)`,
    );
    for (const o of report.offenders) {
      console.log(
        `   +${String(o.over).padStart(3)}px  <${o.tag}> .${o.cls || "(class 無し)"}  w=${o.w} left=${o.left}  ${JSON.stringify(o.text)}`,
      );
    }
    if (!report.offenders.length) console.log("   画面の右端を超える要素は無し");

    if (report.internal.length) {
      console.log("   中身が自分の幅を超えている要素(overflowX が visible なら親を押す):");
      for (const i of report.internal) {
        console.log(
          `   +${String(i.extra).padStart(3)}px  <${i.tag}> .${i.cls || "(class 無し)"}  ` +
            `client=${i.clientWidth} scroll=${i.scrollWidth} overflow-x=${i.overflowX}  ${JSON.stringify(i.text)}`,
        );
      }
    }
    await page.close();
  }
} finally {
  await browser.close();
  server.close();
}
