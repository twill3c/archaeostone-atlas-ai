/**
 * ビルドの刻印の検査(T-410〜T-414 / HC-148)。
 *
 * 本番検品は「健やかか」しか答えない。デプロイが日次上限で落ちた直後でも、
 * 古い本番は健やかなので全項目合格を返す。「新しいか」は刻印で見る。
 *
 * 刻印の射程を二つの実例から決める。
 * - データだけから作ると、フッタのリンクを直しても刻印が変わらない(jinja-origin 2026-09-09)
 * - 改行を揃えずに測ると、作業ツリー(CRLF)と配信側(LF)で必ず食い違う(mondo-atlas)
 */

import { mkdtempSync, mkdirSync, writeFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
// @ts-expect-error — .mjs の型宣言は持たない
import { computeStamp, stampedFiles } from "../scripts/build_stamp.mjs";

function tree(files: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), "stamp-"));
  for (const [rel, body] of Object.entries(files)) {
    const full = join(root, rel);
    mkdirSync(join(full, ".."), { recursive: true });
    writeFileSync(full, body);
  }
  return root;
}

const BASE = {
  "public/data/a.json": '{"n": 1}\n',
  "public/data/b.json": '{"n": 2}\n',
  "app/page.tsx": "export default function P() { return null; }\n",
  "app/globals.css": "body { color: black; }\n",
  "components/Footer.tsx": 'const APP_MENU_URL = "https://app-menu-amber.vercel.app/";\n',
  "lib/evidence.ts": "export const X = 1;\n",
};

describe("build_stamp", () => {
  it("T-410: 同じ木からは同じ刻印", () => {
    const root = tree(BASE);
    expect(computeStamp(root).stamp).toBe(computeStamp(root).stamp);
  });

  it("T-411: 改行が CRLF でも LF でも同じ刻印", () => {
    const lf = tree(BASE);
    const crlf = tree(
      Object.fromEntries(Object.entries(BASE).map(([k, v]) => [k, v.split("\n").join("\r\n")])),
    );
    expect(computeStamp(crlf).stamp).toBe(computeStamp(lf).stamp);
  });

  it("T-412: 画面のソースを変えると刻印が変わる(データだけでなく)", () => {
    const before = tree(BASE);
    const after = tree({
      ...BASE,
      "components/Footer.tsx": 'const APP_MENU_URL = "https://app-menu-tau.vercel.app/";\n',
    });
    expect(computeStamp(after).stamp).not.toBe(computeStamp(before).stamp);
  });

  it("T-413(陽性対照): データだけの刻印はソースの変更を見落とす", () => {
    // 刻印の材料をデータに限った場合を、同じ木で再現する。
    const before = tree(BASE);
    const after = tree({
      ...BASE,
      "components/Footer.tsx": 'const APP_MENU_URL = "https://app-menu-tau.vercel.app/";\n',
    });
    const dataOnly = (root: string) =>
      (computeStamp(root).files as { path: string; sha: string }[])
        .filter((f) => f.path.startsWith("public/data/"))
        .map((f) => f.sha)
        .join(",");
    expect(dataOnly(after)).toBe(dataOnly(before));
  });

  it("T-414: 実際の public/data の JSON を全部材料にしている(手書きの一覧で漏らさない)", () => {
    const root = join(__dirname, "..");
    const listed = new Set(stampedFiles(root) as string[]);
    const actual = readdirSync(join(root, "public", "data"))
      .filter((n) => n.endsWith(".json"))
      .map((n) => `public/data/${n}`);
    expect(actual.length).toBeGreaterThanOrEqual(6);
    for (const path of actual) expect(listed.has(path)).toBe(true);
    expect([...listed].some((p) => p.startsWith("components/"))).toBe(true);
    expect([...listed].some((p) => p.startsWith("app/"))).toBe(true);
  });
});
