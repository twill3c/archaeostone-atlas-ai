import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { AttributionBar } from "@/components/AttributionBar";

export const metadata: Metadata = {
  title: {
    default: "ArchaeoStone Atlas AI — 黒曜石原産地と足もとの地質",
    template: "%s | ArchaeoStone Atlas AI",
  },
  description:
    "日本の黒曜石原産地を、産総研シームレス地質図と重ねて配る研究・教育向けアトラス。" +
    "文献の事実とモデル推定を根拠の階段で分けて示す。",
};

/**
 * 出来た画面だけを並べる。**存在しない先へのリンクを出さない** ——
 * 作る予定のものを先に置くと、空の画面が「まだ何も無い」ではなく
 * 「壊れている」に見える。各ループで画面が出来たらここへ足す。
 */
const NAV = [
  { href: "/", label: "ホーム" },
  { href: "/map", label: "地図" },
  { href: "/sources", label: "原産地" },
  { href: "/geology", label: "地質の偏り" },
  { href: "/jade", label: "ヒスイ集計" },
  { href: "/documents", label: "文献の分布" },
  { href: "/ai-lab", label: "AI ラボ" },
  { href: "/methodology", label: "方法" },
  { href: "/licenses", label: "出典と権利" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <a href="#main" className="skip">
          本文へ移動
        </a>
        <header className="site-header">
          <div className="site-header__inner">
            <Link href="/" className="site-title">
              ArchaeoStone&nbsp;Atlas&nbsp;AI
            </Link>
            <nav aria-label="主要ナビゲーション">
              <ul className="site-nav">
                {NAV.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </header>

        <main id="main">{children}</main>

        <AttributionBar />
      </body>
    </html>
  );
}
