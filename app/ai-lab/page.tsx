import type { Metadata } from "next";
import Link from "next/link";
import { FEATURE_LABELS, likenessCard, xrfCard, type Counts } from "@/lib/data/modelCards";

export const metadata: Metadata = {
  title: "AI ラボ",
  description:
    "地質から原産地らしさを当てる分類器を、事前に宣言した規則で判定する。蛍光X線による原産地推定は No-Go の根拠を項目ごとに示す。",
};

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function CountsRow({ label, counts, nPos, nNeg }: { label: string; counts: Counts; nPos: number; nNeg: number }) {
  return (
    <tr>
      <td>{label}</td>
      <td className="mono">{counts.balanced_accuracy.toFixed(4)}</td>
      <td className="mono">
        {counts.tp}/{nPos}
      </td>
      <td className="mono">
        {counts.fp}/{nNeg}
      </td>
    </tr>
  );
}

export default function AiLabPage() {
  const likeness = likenessCard();
  const xrf = xrfCard();
  const m = likeness.metrics;
  const g10 = likeness.g10;
  const established = g10.verdict === "成立";
  const selectedRules = Object.entries(m.rule.selected_rule_counts);
  const metGo = xrf.go_criteria.filter((c) => c.met).length;

  return (
    <div className="prose-wide">
      <h1>AI ラボ</h1>
      <p className="lede">
        ここにあるのは<strong>モデル推定</strong>(根拠の階段 Level D)である。
        地図や原産地の頁にある文献・地質の事実とは分けて扱う。
      </p>

      <section>
        <h2>地質から「原産地らしさ」を当てる</h2>
        <p>{likeness.task}。</p>

        <div className="notice">
          <p>
            <strong>この分類器は「地質の偏り」の頁の主張(H-01〜H-03)の確認にはならない。</strong>{" "}
            同じデータ・同じ計器から作った特徴で当てているので、当たるのは当然である。
            ここで問うのは一つだけ ——
            <strong>学習した組み合わせが、訓練側で選んだ単一規則を超えるか</strong>。
          </p>
        </div>

        <article className={`claim claim--${established ? "yes" : "no"}`}>
          <header className="claim__head">
            <span className="claim__id mono">G-10</span>
            <span className={`badge ${established ? "badge--yes" : "badge--no"}`}>{g10.verdict}</span>
          </header>
          <p className="claim__statement">{likeness.summary}</p>

          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>方法</th>
                  <th>平衡正解率</th>
                  <th>原産地を当てた</th>
                  <th>対照点を誤って原産地とした</th>
                </tr>
              </thead>
              <tbody>
                <CountsRow label="多数決(全部「原産地でない」)" counts={m.majority} nPos={m.n_positive} nNeg={m.n_negative} />
                <CountsRow label="訓練側で選んだ単一規則" counts={m.rule} nPos={m.n_positive} nNeg={m.n_negative} />
                <CountsRow label="ロジスティック回帰" counts={m.logistic} nPos={m.n_positive} nNeg={m.n_negative} />
              </tbody>
            </table>
          </div>

          <p className="claim__verdict-note">
            差 <span className="mono">{g10.difference >= 0 ? "+" : ""}{g10.difference.toFixed(4)}</span> /
            事前に宣言した幅 <span className="mono">{g10.margin}</span>。
            正例は {m.n_positive} 件しかないので、平衡正解率は正例 1 件で約{" "}
            <span className="mono">{g10.resolution_per_positive.toFixed(3)}</span> 動く。
          </p>
        </article>

        <h3>単一規則として選ばれたもの</h3>
        <p>
          規則は各折りの<strong>訓練側だけ</strong>で選んだ。{m.n_groups} 折りすべてで選ばれたのは次の規則である。
        </p>
        <ul>
          {selectedRules.map(([rule, count]) => (
            <li key={rule}>
              {FEATURE_LABELS[rule] ?? rule} —— {count} 折り
            </li>
          ))}
        </ul>
        <p>
          学習モデルとの差はすべて<strong>誤って原産地とした対照点の数</strong>に出ている(
          {m.rule.fp} → {m.logistic.fp})。原産地を当てた数は同じ {m.logistic.tp}/{m.n_positive} である。
        </p>

        <h3>当たっていること自体は偶然ではない</h3>
        <p>
          ラベルを並べ替えて {m.logistic.permutation.n} 回やり直すと、平衡正解率の平均は{" "}
          <span className="mono">{m.logistic.permutation.mean?.toFixed(4)}</span>、最大でも{" "}
          <span className="mono">{m.logistic.permutation.max?.toFixed(4)}</span> にとどまった
          (置換 p = <span className="mono">{m.logistic.permutation.p?.toFixed(4)}</span>)。
          地質の特徴で原産地を見分けられることは成り立つ ——
          <strong>ただし一つの規則で足りる</strong>。
        </p>

        <h3>分け方</h3>
        <p>
          {likeness.split}。無作為に分けると、同じ火山体の原産地と対照点が訓練と試験に割れ、
          位置の近さを覚えるだけで当たってしまう。
        </p>

        <h3>判定の規則(走らせる前に書いた)</h3>
        <p className="count">{g10.rule}</p>

        <h3>限界</h3>
        <ul>
          {likeness.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>蛍光X線による原産地推定 —— No-Go</h2>
        <p>{xrf.task}。</p>
        <div className="notice">
          <p>
            <strong>このモデルは作っていない。</strong> {xrf.summary}
          </p>
        </div>

        <h3>
          Go 基準 <span className="count">満たすもの {metGo} / {xrf.go_criteria.length}</span>
        </h3>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>基準</th>
                <th>判定</th>
                <th>根拠</th>
              </tr>
            </thead>
            <tbody>
              {xrf.go_criteria.map((criterion) => (
                <tr key={criterion.name}>
                  <td>{criterion.name}</td>
                  <td>
                    <span className={`badge ${criterion.met ? "badge--yes" : "badge--no"}`}>
                      {criterion.met ? "満たす" : "満たさない"}
                    </span>
                  </td>
                  <td className="count">{criterion.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3>No-Go の引き金</h3>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>引き金</th>
                <th>状態</th>
                <th>根拠</th>
              </tr>
            </thead>
            <tbody>
              {xrf.no_go_triggers.map((trigger) => (
                <tr key={trigger.name}>
                  <td>{trigger.name}</td>
                  <td>
                    {trigger.triggered === null ? (
                      <span className="badge">判定不能</span>
                    ) : (
                      <span className={`badge ${trigger.triggered ? "badge--no" : "badge--yes"}`}>
                        {trigger.triggered ? "立つ" : "立たない"}
                      </span>
                    )}
                  </td>
                  <td className="count">
                    {trigger.evidence}
                    {trigger.instruments_seen && (
                      <>
                        <br />
                        機器: <span className="mono">{trigger.instruments_seen.join(" / ")}</span>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>{xrf.method_reference}。</p>
        <p>
          「判定不能」は「引き金が立たない」ではない。調べる対象(ラベルつきの測定値)が無いので、
          調べられなかったことをそのまま書いている。資料の権利については{" "}
          <Link href="/licenses">出典と権利</Link> を参照。
        </p>
      </section>

      <section>
        <h2>訓練しなかったもの</h2>
        <ul>
          <li>
            <strong>深層学習(MLP など)</strong> —— 正例 {m.n_positive} 件では、表現学習が単一規則を超える余地を
            検証すること自体が成り立たない。上の比較でも、線形モデルが規則を宣言した幅で超えなかった。
          </li>
          <li>
            <strong>異常検知</strong> —— 「周辺と比べて特徴が異なる」を言うには出土資料の個票が要るが、
            それは配れない(<Link href="/licenses">出典と権利</Link>)。
          </li>
        </ul>
      </section>
    </div>
  );
}
