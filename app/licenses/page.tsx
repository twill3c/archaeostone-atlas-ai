import type { Metadata } from "next";
import {
  LICENSES,
  redistributableSources,
  restrictedSources,
  type SourceLicense,
} from "@/lib/data/licenses";

export const metadata: Metadata = {
  title: "出典と権利",
  description:
    "本アトラスが使っている源と、使えるが配れない源を、権利表示の実測引用つきで示す。",
};

function SourceCard({ source }: { source: SourceLicense }) {
  return (
    <article className="license-card">
      <header className="license-card__head">
        <h3>{source.title}</h3>
        <span
          className={`badge ${source.redistribution ? "badge--yes" : "badge--no"}`}
        >
          {source.redistribution ? "再配布可" : "再配布不可"}
        </span>
      </header>

      <dl className="license-card__meta">
        <dt>識別子</dt>
        <dd className="mono">{source.source_id}</dd>

        <dt>ライセンス</dt>
        <dd>
          <a href={source.license_url} target="_blank" rel="noreferrer">
            {source.license_name}
          </a>
        </dd>

        <dt>出典表記</dt>
        <dd>{source.attribution_text ?? "不要"}</dd>

        <dt>改変</dt>
        <dd>{source.modification ? "可" : "不可"}</dd>

        <dt>権利表示を読んだ日</dt>
        <dd className="mono">{source.verified_at}</dd>

        <dt>入口</dt>
        <dd>
          <a href={source.source_url} target="_blank" rel="noreferrer">
            {source.source_url}
          </a>
        </dd>
      </dl>

      <blockquote className="license-card__quote">{source.license_quote}</blockquote>

      {source.redistribution_reason && (
        <p className="license-card__reason">
          <strong>本アトラスでの扱い:</strong> {source.redistribution_reason}
        </p>
      )}
    </article>
  );
}

export default function LicensesPage() {
  const usable = redistributableSources();
  const restricted = restrictedSources();

  return (
    <div className="prose-wide">
      <h1>出典と権利</h1>
      <p className="lede">
        源ごとに<strong>「取れるか」と「配れるか」を別々に</strong>確かめてある。
        取得が成功することは、配ってよいことの証拠ではない。
        引用はいずれも {LICENSES.sources[0]?.verified_at} 前後に当該ページを読んで写したものである。
      </p>

      <div className="notice">
        <p>
          このアトラスは <strong>fail-closed</strong> で作ってある。
          再配布可と確かめられていない源に由来するレコードは、公開ファイルへ書き出せない
          (検査 G-01)。だから下の「配れない源」の節にあるデータは、
          この画面にも地図にも<strong>一行も載っていない</strong>。
        </p>
      </div>

      <section>
        <h2>
          使っている源 <span className="count">{usable.length} 件</span>
        </h2>
        <div className="license-grid">
          {usable.map((source) => (
            <SourceCard key={source.source_id} source={source} />
          ))}
        </div>
      </section>

      <section>
        <h2>
          配れない源 <span className="count">{restricted.length} 件</span>
        </h2>
        <p>
          いずれも到達でき、中身も期待どおりだった。壁は権利のほうにある。
          <strong>載せないと「使っていない」と「隠している」が区別できない</strong>ので、
          理由ごと残す。
        </p>
        <div className="license-grid">
          {restricted.map((source) => (
            <SourceCard key={source.source_id} source={source} />
          ))}
        </div>
      </section>

      <section>
        <h2>本アトラス自身</h2>
        <p>
          コードと、本プロジェクトが編纂した原産地辞書は MIT ライセンスで配る。
          辞書の各項目は典拠と座標の出所を持つ(方法の頁を参照)。
        </p>
      </section>
    </div>
  );
}
