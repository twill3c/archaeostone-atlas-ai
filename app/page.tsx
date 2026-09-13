import Link from "next/link";
import { EVIDENCE_LADDER } from "@/lib/evidence";
import { LICENSES } from "@/lib/data/licenses";

export default function HomePage() {
  const { counts } = LICENSES;

  return (
    <div className="home">
      <section className="home__hero prose">
        <h1>黒曜石の原産地と、その足もとの地質</h1>
        <p className="lede">
          日本の黒曜石原産地を、産総研の 20 万分の 1 シームレス地質図と重ねて配る
          アトラスである。あわせて、ヒスイの出土集成と全国の発掘調査報告書の分布を、
          <strong>根拠の階段ごとに分けて</strong>同じ地図に載せる。
        </p>
        <p>
          このアトラスが最初に測るのは、次の一つの問いである ——
          <strong>
            黒曜石の原産地の足もとの地質は、無作為に選んだ陸地点と比べて、どれだけ偏っているか。
          </strong>
          原産地の一覧は考古・岩石学の文献から編み、地質図はそれとは独立に産総研が作っている。
          だから両者を突き合わせても循環しない。
        </p>
      </section>

      <section className="home__cards">
        <Link href="/map" className="card">
          <h2>地図</h2>
          <p>地理院の底図に地質図を重ね、典拠つきの原産地を置く。</p>
        </Link>
        <Link href="/geology" className="card">
          <h2>地質の偏り</h2>
          <p>原産地と対照群を順列検定で比べる。落ちた主張も載せる。</p>
        </Link>
        <Link href="/sources" className="card">
          <h2>原産地</h2>
          <p>一件ずつ、座標の出所と典拠と足もとの地質を示す。</p>
        </Link>
        <Link href="/jade" className="card">
          <h2>ヒスイ集計</h2>
          <p>個票は配らず、源の内部にある三つの照合の結果を示す。</p>
        </Link>
        <Link href="/documents" className="card">
          <h2>文献の分布</h2>
          <p>報告書 33 万件の題名を全件走査し、石材の語を数えた。</p>
        </Link>
        <Link href="/ai-lab" className="card">
          <h2>AI ラボ</h2>
          <p>学習モデルは単一規則を超えたか。事前に宣言した規則で判定する。</p>
        </Link>
        <Link href="/methodology" className="card">
          <h2>方法</h2>
          <p>座標をどう決め、地質をどう付け、何を測らないかを述べる。</p>
        </Link>
        <Link href="/licenses" className="card">
          <h2>出典と権利</h2>
          <p>源ごとに「取れるか」と「配れるか」を別々に示す。</p>
        </Link>
      </section>

      <section className="home__ladder">
        <h2>根拠の階段</h2>
        <p className="prose">
          画面に出るあらゆる主張は、この 5 段のどれかに属する。属さないものは出さない。
          色だけでは区別しない —— 線種と記号も併せて変える。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>段</th>
                <th>名称</th>
                <th>何に支えられているか</th>
                <th>地図での線</th>
              </tr>
            </thead>
            <tbody>
              {EVIDENCE_LADDER.map((level) => (
                <tr key={level.level}>
                  <td>
                    <span
                      className="ev-chip"
                      style={{ color: `var(${level.cssVar})` }}
                    >
                      Level {level.level}
                    </span>
                  </td>
                  <td>{level.labelJa}</td>
                  <td>{level.basis}</td>
                  <td className="mono">{level.stroke}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="home__honesty">
        <div className="notice">
          <p>
            <strong>配っていないデータがある。</strong>{" "}
            採録を検討した源 {counts.total} 件のうち、{counts.not_redistributable} 件は
            権利表示・robots.txt により再配布できない。取得できることと配れることは
            別なので、その {counts.not_redistributable} 件は
            <strong>理由ごと</strong>
            <Link href="/licenses">出典と権利</Link>
            に載せてある。隠して「使っていない」ように見せることはしない。
          </p>
        </div>
      </section>
    </div>
  );
}
