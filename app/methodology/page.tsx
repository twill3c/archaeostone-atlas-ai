import type { Metadata } from "next";
import Link from "next/link";
import { EVIDENCE_LADDER } from "@/lib/evidence";

export const metadata: Metadata = {
  title: "方法",
  description:
    "原産地の座標をどう決めたか、地質をどう付けたか、何を測って何を測らないかを述べる。",
};

export default function MethodologyPage() {
  return (
    <div className="prose-wide">
      <h1>方法</h1>
      <p className="lede">
        このアトラスは、測っていないことを測ったように見せないために作られている。
        以下は、値がどこから来て、どこで止まるかの説明である。
      </p>

      <section>
        <h2>原産地の座標をどう決めるか</h2>
        <p>
          黒曜石原産地の座標は、<strong>推測で埋めない</strong>。手順は三段である。
        </p>
        <ol>
          <li>
            地名を国土地理院の地名検索へ投げ、<strong>候補を全部保存する</strong>。
          </li>
          <li>
            候補から一つを選ぶ。<strong>選んだ理由と候補番号を記録する</strong> ——
            レコードの <code>coordinate_provenance</code> に、問い合わせ語・
            何番目の候補か・候補の表示名が残る。
          </li>
          <li>
            選べない、または候補が 0 件の場合は <code>needs_review</code> のまま出荷し、
            画面でもそう表示する。
          </li>
        </ol>
        <div className="notice">
          <p>
            <strong>上位 1 件を正解にしてはならない。</strong> 実測(2026-09-08)では、
            「和田峠」の 1 位は青森県七戸町和田、「腰岳」の 1 位は沖縄の腰岳だった。
            どちらも黒曜石原産地ではない。地名検索は<strong>候補生成器</strong>であって
            同定器ではない。
          </p>
        </div>
      </section>

      <section>
        <h2>地質をどう付けるか</h2>
        <p>
          各地点の地質は、産総研 20 万分の 1 日本シームレス地質図 V2 の地点問い合わせ
          から取る。この API は「地質が無い」を<strong>三通りの形</strong>で返すので、
          取得器はそれを取り違えないように書いてある。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>応答</th>
                <th>本アトラスの判定</th>
                <th>再試行</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>200 + 全項目</td>
                <td>地質あり</td>
                <td>しない</td>
              </tr>
              <tr>
                <td>
                  200 + <code>symbol: null</code>
                </td>
                <td>図郭内・ポリゴン無し(内水面など)</td>
                <td>しない</td>
              </tr>
              <tr>
                <td>
                  <strong>HTTP 500 + 本文 0 バイト</strong>
                </td>
                <td>被覆外</td>
                <td>
                  <strong>しない</strong>
                </td>
              </tr>
              <tr>
                <td>接続断・タイムアウト</td>
                <td>通信の失敗</td>
                <td>する(間を空けて 4 回まで)</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          三行目が肝心である。5xx は再試行の階級として広く実装されているが、
          ここでの 500 は障害ではなく<strong>「被覆外」という答え</strong>である。
          状態コードの階級だけで再試行を決めると、湖上や海上の地点ごとに
          最大回数まで待つことになる。
        </p>
        <p>
          あわせて、API が返す <code>title</code> は
          <code>formationAge_ja + &quot;,&quot; + lithology_ja</code> の連結にすぎない。
          両方が空のとき文字列 <code>&quot;,&quot;</code> になり、
          <strong>空文字ではないので真偽判定では通ってしまう</strong>。
          だから <code>title</code> は表示にしか使わず、判定は <code>symbol</code> で行う。
        </p>
      </section>

      <section>
        <h2>根拠の階段</h2>
        <p>
          画面のあらゆる主張は、次の 5 段のどれかに属する。
          <strong>記号は仕様の述語に対応している</strong> ——
          色や線種は「確からしさの強弱」ではなく「何に支えられているか」を表す。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>段</th>
                <th>名称</th>
                <th>支え</th>
                <th>線</th>
              </tr>
            </thead>
            <tbody>
              {EVIDENCE_LADDER.map((level) => (
                <tr key={level.level}>
                  <td>
                    <span className="ev-chip" style={{ color: `var(${level.cssVar})` }}>
                      {level.level}
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

      <section>
        <h2>測らないこと</h2>
        <ul>
          <li>
            <strong>石材の出土地点は地図に出さない。</strong> 出土の集成表は再配布できない
            (<Link href="/licenses">出典と権利</Link>)。ヒスイは集計だけを出す。
          </li>
          <li>
            <strong>蛍光X線分析による原産地推定は行わない。</strong>{" "}
            再利用条件の明確なラベル付き実測データが無く、構想書 §34 の No-Go 基準
            (ラベルが文献ごとに不整合・測定装置差の補正なし・権利状態不明)に該当する。
            モデルカードだけを出し、UI では無効にする。
          </li>
          <li>
            <strong>推定移動ルート・流通ネットワークは出さない。</strong>{" "}
            距離と類似度は測れるが、それを「交易路」と呼ぶ根拠が無い。
          </li>
          <li>
            <strong>発掘調査報告書の本文は扱わない。</strong>{" "}
            本文の著作権は発行自治体ごとにあり、31 万件規模で個別許諾は取れない。
            使うのは索引メタデータだけである。
          </li>
        </ul>
      </section>

      <section>
        <h2>再現のしかた</h2>
        <p>公開ファイルはすべて、次の一連から作られる。</p>
        <pre className="scroll-x">
          <code>{`python -m pipeline.export_licenses
python -m pipeline.acquisition.nabunken
python -m pipeline.build_source_areas
python -m pipeline.build_control_points
python -m pipeline.build_geology_stats
python -m pipeline.build_documents
python -m pipeline.build_model_cards`}</code>
        </pre>
        <p>
          再配布できない源(糸魚川市のヒスイ集成表)は、リポジトリに含まれていない。
          手元で取得すると、集計に加えて個票の検査も走る。
        </p>
        <pre className="scroll-x">
          <code>{`python -m pipeline.acquisition.itoigawa
python -m pipeline.build_jade_aggregate`}</code>
        </pre>
      </section>
    </div>
  );
}
