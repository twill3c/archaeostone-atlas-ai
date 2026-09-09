import type { Metadata } from "next";
import Link from "next/link";
import { GEOLOGY_STATS, geologyColour, type Claim } from "@/lib/data/atlas";

export const metadata: Metadata = {
  title: "地質の偏り",
  description:
    "黒曜石原産地の足もとの地質を、無作為な陸地点と比べる。順列検定の結果を、落ちた主張も含めて示す。",
};

function formatP(p: number | null): string {
  if (p === null) return "検定不可";
  if (p === 0) return "p < 0.00005";
  return `p = ${p.toFixed(5)}`;
}

function ClaimCard({ claim }: { claim: Claim }) {
  const established = claim.verdict === "成立";
  return (
    <article className={`claim claim--${established ? "yes" : "no"}`}>
      <header className="claim__head">
        <span className="claim__id mono">{claim.claim_id}</span>
        <span className={`badge ${established ? "badge--yes" : "badge--no"}`}>
          {claim.verdict}
        </span>
      </header>
      <p className="claim__statement">{claim.statement}</p>

      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th>条件</th>
              <th>原産地</th>
              <th>対照群</th>
              <th>差</th>
              <th>p 値</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(claim.variants).map(([name, variant]) => {
              const significant = variant.p_value !== null && variant.p_value < 0.05;
              return (
                <tr key={name}>
                  <td>{name}</td>
                  <td className="mono">
                    {variant.source_proportion === null
                      ? "—"
                      : `${(variant.source_proportion * 100).toFixed(1)}%`}
                    <span className="claim__n"> (n={variant.source_n})</span>
                  </td>
                  <td className="mono">
                    {variant.control_proportion === null
                      ? "—"
                      : `${(variant.control_proportion * 100).toFixed(1)}%`}
                    <span className="claim__n"> (n={variant.control_n})</span>
                  </td>
                  <td className="mono">
                    {variant.observed_difference === null
                      ? "—"
                      : `${variant.observed_difference > 0 ? "+" : ""}${variant.observed_difference.toFixed(3)}`}
                  </td>
                  <td className={`mono ${significant ? "sig" : "nonsig"}`}>
                    {formatP(variant.p_value)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="claim__verdict-note">{claim.verdict_note}</p>
    </article>
  );
}

function DistributionBars({
  title,
  counts,
  total,
}: {
  title: string;
  counts: Record<string, number>;
  total: number;
}) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <div className="dist">
      <h3>
        {title} <span className="count">測れた {total} 件</span>
      </h3>
      <ul className="dist__list">
        {entries.map(([group, n]) => {
          const share = total > 0 ? n / total : 0;
          return (
            <li key={group}>
              <span className="dist__label">{group}</span>
              <span className="dist__track">
                <span
                  className="dist__fill"
                  style={{
                    width: `${Math.max(share * 100, 0.7)}%`,
                    background: geologyColour(group),
                  }}
                />
              </span>
              <span className="dist__value mono">
                {n} <span className="count">({(share * 100).toFixed(1)}%)</span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function GeologyPage() {
  const { method, distributions, claims } = GEOLOGY_STATS;
  const established = claims.filter((c) => c.verdict === "成立");
  const dropped = claims.filter((c) => c.verdict !== "成立");

  return (
    <div className="prose-wide">
      <h1>地質の偏り</h1>
      <p className="lede">
        黒曜石原産地の足もとの地質を、日本の陸域から面積の重みで無作為に選んだ
        {distributions.control_points.n} 点と比べた。
        <strong>
          {established.length} 件の主張が成立し、{dropped.length} 件は成立しなかった。
        </strong>
        落ちた主張も消さずに載せる。
      </p>

      <div className="notice">
        <p>
          <strong>判定の規則を先に決めてある。</strong> {method.verdict_rule}
        </p>
      </div>

      <section>
        <h2>分布</h2>
        <div className="dist-grid">
          <DistributionBars
            title="黒曜石原産地の地質(大分類)"
            counts={distributions.source_areas.group_ja}
            total={distributions.source_areas.n_measured}
          />
          <DistributionBars
            title="対照群(無作為な陸地点)"
            counts={distributions.control_points.group_ja}
            total={distributions.control_points.n_measured}
          />
        </div>
      </section>

      <section>
        <h2>成立した主張</h2>
        {established.map((claim) => (
          <ClaimCard key={claim.claim_id} claim={claim} />
        ))}
      </section>

      <section>
        <h2>成立しなかった主張</h2>
        <p>
          こちらのほうが読む価値がある。
          <strong>期待した向きに差はあるのに、切り方を変えると有意性が入れ替わる。</strong>
        </p>
        {dropped.map((claim) => (
          <ClaimCard key={claim.claim_id} claim={claim} />
        ))}
      </section>

      <section>
        <h2>なぜ細分の主張が弱いのか</h2>
        <p>{method.limitation}</p>
        <p>
          つまり <strong>個々の原産地に付いた岩相の label は、黒曜石そのものの岩相ではない</strong>。
          「安山岩」と出た原産地に黒曜石が無いのではなく、
          20 万分の 1 の図郭が黒曜石の岩体を分離できていない。
        </p>
      </section>

      <section>
        <h2>この比較が循環していないこと</h2>
        <p>{method.non_circularity}</p>
        <h3>対照群の作り方</h3>
        <p>{method.control_group}</p>
        <p>
          検定は{method.test}、反復 {method.iterations.toLocaleString()} 回、
          種 <span className="mono">{method.seed}</span>。同じ種なら同じ p 値が出る。
          手順の詳細は <Link href="/methodology">方法</Link> にある。
        </p>
      </section>
    </div>
  );
}
