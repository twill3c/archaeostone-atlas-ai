import Link from "next/link";
import { attributions } from "@/lib/data/licenses";
import Footer from "./Footer";

/**
 * 出典パネル(構想書 §36)。
 *
 * 「画面フッターまたは About data から常時アクセス可能にする」が要件なので、
 * 全ページの下端に置く。出典表記は `config/sources.yaml` の実測から生成しており、
 * 画面に手で書いた文字列ではない —— 権利表示が変わったら 1 箇所を直せば全画面に届く。
 */
export function AttributionBar() {
  const items = attributions();

  return (
    <>
      <section className="attribution" aria-labelledby="attribution-heading">
        <h2 id="attribution-heading" className="attribution__heading">
          出典
        </h2>
        <ul className="attribution__list">
          {items.map((item) => (
            <li key={item.source_id}>
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.text}
              </a>
            </li>
          ))}
        </ul>
        <p className="attribution__note">
          地理院タイル・シームレス地質図は加工して表示している。
          権利の詳細と、本アトラスが<strong>配っていないデータ</strong>については{" "}
          <Link href="/licenses">出典と権利</Link> を参照。
        </p>
      </section>
      <Footer />
    </>
  );
}
