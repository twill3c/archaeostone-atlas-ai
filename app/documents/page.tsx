import type { Metadata } from "next";
import Link from "next/link";
import {
  COMPLETE_LIST_SIZE,
  DOCUMENTS,
  MATERIAL_LABELS,
  materialMentionsRanked,
} from "@/lib/data/documents";

export const metadata: Metadata = {
  title: "文献の分布",
  description:
    "全国遺跡報告総覧 33 万件の題名を全件走査し、石材の語がどれだけ現れるかを数えた。",
};

export default function DocumentsPage() {
  const { corpus, material_mentions: mentions, by_prefecture } = DOCUMENTS;
  const ranked = materialMentionsRanked();
  const maxPrefecture = Math.max(...by_prefecture.map((p) => p.documents));
  const shapes = corpus.record_shapes;
  const gap = corpus.records - COMPLETE_LIST_SIZE;

  return (
    <div className="prose-wide">
      <h1>文献の分布</h1>
      <p className="lede">
        全国遺跡報告総覧を OAI-PMH で全件収穫し、{corpus.pages_parsed.toLocaleString()} ページ
        {corpus.records.toLocaleString()} 件の題名を走査した。
        石材の語がどれだけ現れるかを数えると、
        <strong>いちばん多い黒曜石でも 0.094%</strong> である。
      </p>

      <div className="notice">
        <p>
          <strong>これは「石材が出土した遺跡の分布」ではない。</strong> {mentions.note}
          発掘調査報告書の題名は遺跡名と叢書名が主なので、石材はまれにしか現れない。
          現れるのは「鷹山遺跡群」「長野県黒耀石原産地遺跡分布調査報告書」のような、
          <strong>原産地そのものを調査した報告書</strong>である。
        </p>
      </div>

      <section>
        <h2>題名に現れた石材の語</h2>
        <p>
          分母は<strong>メタデータのあるレコード {mentions.denominator.toLocaleString()} 件</strong>。
          取り下げられたレコード({shapes.no_metadata.toLocaleString()} 件)は題名を持たないので除く。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>石材</th>
                <th>検索語</th>
                <th>件数</th>
                <th>率</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map(([key, entry]) => (
                <tr key={key}>
                  <td>{MATERIAL_LABELS[key] ?? key}</td>
                  <td className="count">{entry.terms.join("・")}</td>
                  <td className="mono">{entry.hits.toLocaleString()}</td>
                  <td className="mono">
                    {entry.rate === null ? "—" : `${(entry.rate * 100).toFixed(4)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3>分析方法の語</h3>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>語</th>
                <th>件数</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(mentions.method_terms).map(([term, hits]) => (
                <tr key={term}>
                  <td>{term}</td>
                  <td className="mono">{hits.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>黒曜石に触れる報告書の例</h2>
        <ul>
          {(DOCUMENTS.material_mentions.counts.obsidian?.examples ?? [])
            .slice(0, 6)
            .map((example, index) => (
              <li key={`${example.url ?? index}`}>
                {example.url ? (
                  <a href={example.url} target="_blank" rel="noreferrer">
                    {example.title}
                  </a>
                ) : (
                  example.title
                )}
              </li>
            ))}
        </ul>
      </section>

      <section>
        <h2>源の公表する総数が、源自身の返す件数と合わない</h2>
        <p>
          収穫した総数は <strong>{corpus.records.toLocaleString()} 件</strong>だが、
          OAI の <code>resumptionToken</code> が名乗る{" "}
          <code>completeListSize</code> は{" "}
          <strong>{COMPLETE_LIST_SIZE.toLocaleString()} 件</strong>である。
          差 {gap.toLocaleString()} 件は、<strong>junii2 形のレコード数と完全に一致する</strong>。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>レコードの形</th>
                <th>件数</th>
                <th>公表値に数えられているか</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <code>oai_dc</code>(報告書)
                </td>
                <td className="mono">{shapes.oai_dc.toLocaleString()}</td>
                <td>数えられている</td>
              </tr>
              <tr>
                <td>メタデータ無し(取り下げ)</td>
                <td className="mono">{shapes.no_metadata.toLocaleString()}</td>
                <td>数えられている</td>
              </tr>
              <tr>
                <td>
                  <code>junii2</code>(論文)
                </td>
                <td className="mono">{shapes.junii2.toLocaleString()}</td>
                <td>
                  <strong>数えられていない</strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          だから <code>completeListSize</code> を件数の照合に使うと、
          <strong>junii2 を取りこぼした解析器と、正しい解析器が区別できない</strong> ——
          どちらも {COMPLETE_LIST_SIZE.toLocaleString()} になる。
          取りこぼしを検出するつもりの数が、取りこぼしを隠す。
        </p>
      </section>

      <section>
        <h2>都道府県別の報告書数</h2>
        <p>
          <code>setSpec</code> が全国地方公共団体コードを持つので、
          地理コード化は収穫と同時に得られる。市区町村は{" "}
          {DOCUMENTS.municipality_count.toLocaleString()} 種が現れた。
        </p>
        <div className="dist">
          <ul className="dist__list dist__list--wide">
            {[...by_prefecture]
              .sort((a, b) => b.documents - a.documents)
              .map((prefecture) => (
                <li key={prefecture.code}>
                  <span className="dist__label">{prefecture.name}</span>
                  <span className="dist__track">
                    <span
                      className="dist__fill"
                      style={{
                        width: `${Math.max((prefecture.documents / maxPrefecture) * 100, 0.7)}%`,
                        background: "var(--accent)",
                      }}
                    />
                  </span>
                  <span className="dist__value mono">
                    {prefecture.documents.toLocaleString()}
                  </span>
                </li>
              ))}
          </ul>
        </div>
      </section>

      <section>
        <h2>この数の読み方</h2>
        <p>
          収穫したのは<strong>索引のメタデータだけ</strong>である。
          報告書本文 PDF の著作権は発行自治体ごとにあり、31 万件規模で個別許諾は
          取れないので、本文には触れていない(
          <Link href="/licenses">出典と権利</Link>)。
        </p>
        <p>
          したがって「黒曜石 299 件」は<strong>題名に語が現れた報告書の数</strong>であって、
          黒曜石が出土した遺跡の数ではない。本文まで見れば桁が変わるはずだが、
          それは本アトラスが測れる範囲の外にある。
        </p>
      </section>
    </div>
  );
}
