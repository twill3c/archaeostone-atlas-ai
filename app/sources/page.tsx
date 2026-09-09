import type { Metadata } from "next";
import Link from "next/link";
import { SOURCE_AREAS, geologyColour } from "@/lib/data/atlas";

export const metadata: Metadata = {
  title: "原産地",
  description:
    "黒曜石原産地の一覧。一件ずつ、座標の出所(どの問い合わせの何番目の候補か)と典拠と足もとの地質を示す。",
};

export default function SourcesPage() {
  const { source_areas: areas, counts, coverage_note } = SOURCE_AREAS;
  const byGroup = new Map<string, typeof areas>();
  for (const area of areas) {
    const key = area.group_ja ?? "その他";
    byGroup.set(key, [...(byGroup.get(key) ?? []), area]);
  }

  return (
    <div className="prose-wide">
      <h1>黒曜石原産地</h1>
      <p className="lede">
        典拠を確認できた {counts.total} 件。座標はすべて国土地理院の地名検索から引き、
        <strong>どの問い合わせの何番目の候補を、どの規則で選んだか</strong>を
        一件ずつ残してある。手で書いた座標は 1 件も無い。
      </p>

      <div className="notice">
        <p>
          <strong>これは網羅ではない。</strong> {coverage_note}
        </p>
      </div>

      <p>
        {counts.coordinate_precision_area} 件は座標の精度が<strong>概略</strong>である
        (露頭ではなく集落・行政区域の地点)。地図では四角い標で区別し、
        <Link href="/geology">地質の偏り</Link>{" "}
        では、これらを除いた場合の結果も併記している。
      </p>

      {[...byGroup.entries()].map(([group, members]) => (
        <section key={group}>
          <h2>
            {group} <span className="count">{members.length} 件</span>
          </h2>
          <div className="source-grid">
            {members.map((area) => {
              const prov = area.coordinate_provenance;
              return (
                <article key={area.id} className="source-card">
                  <header className="source-card__head">
                    <h3>{area.name_ja}</h3>
                    <span
                      className="source-card__dot"
                      style={{ background: geologyColour(area.geology_group_ja) }}
                      aria-hidden="true"
                    />
                  </header>

                  <p className="source-card__geology">
                    {area.geology_group_ja ? (
                      <>
                        <strong>{area.geology_group_ja}</strong>
                        <br />
                        {area.lithology_ja}
                        <br />
                        <span className="count">{area.formation_age_ja}</span>
                      </>
                    ) : (
                      <span className="passport__absent">
                        図郭にポリゴンが無い(海岸の露頭など)
                      </span>
                    )}
                  </p>

                  <dl className="source-card__meta">
                    <dt>座標</dt>
                    <dd className="mono">
                      {area.latitude?.toFixed(5)}, {area.longitude?.toFixed(5)}
                      {area.coordinate_precision === "area" && (
                        <>
                          {" "}
                          <span className="badge badge--no">概略</span>
                        </>
                      )}
                    </dd>

                    <dt>座標の出所</dt>
                    <dd>
                      「{prov.query}」→ 候補 {prov.candidate_count} 件中{" "}
                      {(prov.candidate_index ?? 0) + 1} 番目「{prov.candidate_title}」
                    </dd>

                    <dt>選んだ規則</dt>
                    <dd className="source-card__rule">{prov.rule}</dd>

                    <dt>典拠</dt>
                    <dd>
                      <ul className="passport__citations">
                        {area.citations.map((citation) => (
                          <li key={citation.citation_id}>
                            <a href={citation.url} target="_blank" rel="noreferrer">
                              {citation.title}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </dd>
                  </dl>

                  {area.note && <p className="source-card__note">{area.note}</p>}
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
