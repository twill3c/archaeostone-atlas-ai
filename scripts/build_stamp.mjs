/**
 * ビルドの刻印を作る(T-410〜T-414 / HC-148)。
 *
 * 本番検品は**本番が健やかか**しか答えない。デプロイが日次上限で落ちた直後でも、
 * 古い本番は健やかなので全項目合格を返す(mondo-atlas 2026-09-03 実地)。
 * そこで配られる木の内容から刻印を作って `public/build-stamp.json` に置き、
 * 検品は本番の刻印を引いて手元の値と突き合わせ、**違えば不合格にする**。
 *
 * 材料は「画面が読むデータ」と「画面のソース」の両方にする。
 * データだけにすると、フッタのリンクを直しただけの配布を刻印が見分けられない
 * (jinja-origin 2026-09-09 —— T-413 がその見落としを陽性対照として再現する)。
 *
 * 一覧は手で書かず、ディレクトリを実際に歩いて作る。書き忘れると刻印が変化を見落とす。
 */

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

/** 刻印の材料にするディレクトリと拡張子。 */
const STAMPED_DIRS = [
  { dir: "public/data", ext: [".json"] },
  { dir: "app", ext: [".ts", ".tsx", ".css"] },
  { dir: "components", ext: [".ts", ".tsx", ".css"] },
  { dir: "lib", ext: [".ts", ".tsx"] },
];

function walk(root, rel, ext) {
  const full = join(root, rel);
  if (!existsSync(full)) return [];
  const found = [];
  for (const name of readdirSync(full).sort()) {
    const childRel = `${rel}/${name}`;
    if (statSync(join(root, childRel)).isDirectory()) {
      found.push(...walk(root, childRel, ext));
    } else if (ext.some((e) => name.endsWith(e))) {
      found.push(childRel);
    }
  }
  return found;
}

export function stampedFiles(root = ROOT) {
  return STAMPED_DIRS.flatMap(({ dir, ext }) => walk(root, dir, ext));
}

/**
 * 改行を揃えてから測る。
 *
 * この機は `core.autocrlf=true` なので、作業ツリーは CRLF・git と配信側は LF になる。
 * 生のバイト列で測ると同じ内容でも手元と本番で必ず食い違い、検査が毎回「違う」と言い続ける。
 */
function normalizeEol(buf) {
  return Buffer.from(buf.toString("utf8").split("\r\n").join("\n"), "utf8");
}

export function computeStamp(root = ROOT) {
  const h = createHash("sha256");
  const files = [];
  for (const rel of stampedFiles(root)) {
    const buf = normalizeEol(readFileSync(join(root, rel)));
    const one = createHash("sha256").update(buf).digest("hex").slice(0, 12);
    files.push({ path: rel, bytes: buf.length, sha: one });
    h.update(rel).update("\0").update(buf).update("\0");
  }
  return { stamp: h.digest("hex").slice(0, 16), files };
}

function main() {
  const out = join(ROOT, "public", "build-stamp.json");
  if (!existsSync(dirname(out))) mkdirSync(dirname(out), { recursive: true });
  const doc = computeStamp();
  writeFileSync(out, JSON.stringify(doc, null, 1));
  console.log(`刻印 ${doc.stamp}(${doc.files.length} ファイル)→ public/build-stamp.json`);
}

if (process.argv[1] && process.argv[1].endsWith("build_stamp.mjs")) main();
