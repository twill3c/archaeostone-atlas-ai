import type { Metadata } from "next";
import Link from "next/link";
import { JADE, TALLY_ORDER, rgbToCss } from "@/lib/data/jade";

export const metadata: Metadata = {
  title: "ヒスイ集計",
  description:
    "糸魚川市ヒスイ出土情報集成表の集計統計。個票は配らず、源の内部にある三つの照合の結果を示す。",
};

export default function JadePage() {
  const { coverage, internal_checks: checks, tallies } = JADE;
  const note = checks.note_vs_sheets;
  const inline = checks.inline_counts_vs_count_column;
  const colour = checks.background_colour_vs_blank_cells;
  const maxRows = Math.max(...coverage.per_sheet.map((s) => s.rows));

  return (
    <div className="prose-wide">
      <h1>ヒスイ集計</h1>
      <p className="lede">
        糸魚川市の集成表から、<strong>件数の集計だけ</strong>を出している。
        {coverage.sheets} シート {coverage.rows} 行、
        点数が記録されているのは {coverage.rows_with_count} 行である。
      </p>

      <div className="notice">
        <p>
          <strong>個票は配っていない。</strong> {JADE.redistribution_notice}
        </p>
      </div>

      <section>
        <h2>収録の範囲</h2>
        <p>{coverage.note}</p>
        <div className="dist">
          <ul className="dist__list dist__list--wide">
            {coverage.per_sheet.map((sheet) => (
              <li key={sheet.sheet}>
                <span className="dist__label">{sheet.sheet}</span>
                <span className="dist__track">
                  <span
                    className="dist__fill"
                    style={{
                      width: `${Math.max((sheet.rows / maxRows) * 100, 0.7)}%`,
                      background: "var(--accent)",
                    }}
                  />
                </span>
                <span className="dist__value mono">{sheet.rows}</span>
              </li>
            ))}
          </ul>
        </div>

        <h3>点数の欄がどれだけ埋まっているか</h3>
        <p>
          <strong>空欄は 0 ではなく「不明」である</strong>
          (註 2「不明な箇所は空欄とした」)。だから合計だけを見てはいけない。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>セルの型</th>
                <th>行数</th>
                <th>意味</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(coverage.count_cell_types).map(([type, n]) => (
                <tr key={type}>
                  <td>{type}</td>
                  <td className="mono">{n}</td>
                  <td className="count">
                    {type === "数値"
                      ? "点数が記録されている"
                      : type === "文字列"
                        ? "「６？」のように数でない記入"
                        : type === "書式のみ"
                          ? "値は無いが書式がある(製作遺跡の色つき行)"
                          : "記入が無い = 不明"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>源の内部にある三つの照合</h2>
        <p>
          いずれも<strong>源の中だけで成り立つ照合</strong>なので、
          こちらの解釈を前提にしていない(循環しない)。
        </p>

        <article className={`claim claim--${note.named_but_missing.length ? "no" : "yes"}`}>
          <header className="claim__head">
            <span className="claim__id mono">{note.gate}</span>
            <span className="badge badge--no">食い違いあり</span>
          </header>
          <p className="claim__statement">註が挙げる県 と 実際のシート</p>
          <p>{note.description}</p>
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>註が担当者を挙げる県</th>
                  <th>実際のデータシート</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="mono">{note.named_in_note.length} 件</td>
                  <td className="mono">{note.sheets.length} 件</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="claim__verdict-note">
            註にあってシートが無い: <strong>{note.named_but_missing.join("・")}</strong>
            {" / "}
            シートにあって註に無い:{" "}
            <strong>{note.present_but_unnamed.join("・")}</strong>
          </p>
        </article>

        <article className="claim claim--no">
          <header className="claim__head">
            <span className="claim__id mono">{inline.gate}</span>
            <span className="badge badge--no">食い違い {inline.disagreements} 件</span>
          </header>
          <p className="claim__statement">種別に埋まった内訳の和 と 点数の欄</p>
          <p>{inline.description}</p>
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>照合できた</th>
                  <th>一致</th>
                  <th>食い違い</th>
                  <th>読めなかった</th>
                  <th>全角数字のみ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="mono">{inline.compared}</td>
                  <td className="mono sig">{inline.agreements}</td>
                  <td className="mono">{inline.disagreements}</td>
                  <td className="mono">{inline.unparsed}</td>
                  <td className="mono">{inline.fullwidth_only}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <h3>食い違った行の記法</h3>
          <p>
            出すのは<strong>種別の書き方</strong>だけで、どの遺跡かは出さない。
          </p>
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>シート</th>
                  <th>種別の記入</th>
                  <th>内訳の和</th>
                  <th>点数の欄</th>
                </tr>
              </thead>
              <tbody>
                {inline.disagreement_notations.map((entry, index) => (
                  <tr key={`${entry.sheet}-${index}`}>
                    <td>{entry.sheet}</td>
                    <td className="mono">{entry.notation}</td>
                    <td className="mono">{entry.inline_total}</td>
                    <td className="mono">{entry.recorded_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className={`claim claim--${colour.match ? "yes" : "no"}`}>
          <header className="claim__head">
            <span className="claim__id mono">{colour.gate}</span>
            <span className={`badge ${colour.match ? "badge--yes" : "badge--no"}`}>
              {colour.match ? "完全一致" : "不一致"}
            </span>
          </header>
          <p className="claim__statement">
            背景色つきの行 と 点数セルが「書式のみ」の行
          </p>
          <p>{colour.description}</p>
          <p>
            色つき <strong className="mono">{colour.flagged_rows}</strong> 行、
            書式のみ <strong className="mono">{colour.blank_count_rows}</strong> 行 ——
            {colour.match ? "完全に一致する" : "一致しない"}。
            対象は {colour.sheets_with_flags.join("・")} のシートのみ。
          </p>
          <p className="claim__verdict-note">
            {colour.observed_colours.map((rgb) => (
              <span key={rgb.join(",")} className="colour-chip">
                <span
                  className="colour-chip__swatch"
                  style={{ background: rgbToCss(rgb) }}
                  aria-hidden="true"
                />
                <span className="mono">rgb({rgb.join(" ")})</span>
              </span>
            ))}{" "}
            {colour.note}
          </p>
        </article>
      </section>

      <section>
        <h2>語彙の分布</h2>
        <p>
          <strong>「不明」と空欄は語彙に数えないが、件数は出す。</strong>
          落とした行を消すと「そういう行が無かった」と読めてしまう。
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr>
                <th>列</th>
                <th>異なり</th>
                <th>記入あり</th>
                <th>「不明」</th>
                <th>空欄</th>
                <th>最多の値</th>
              </tr>
            </thead>
            <tbody>
              {TALLY_ORDER.filter((column) => tallies[column]).map((column) => {
                const tally = tallies[column];
                const [topValue, topCount] = tally.top[0] ?? ["—", 0];
                return (
                  <tr key={column}>
                    <td>{column}</td>
                    <td className="mono">{tally.distinct}</td>
                    <td className="mono">{tally.recorded}</td>
                    <td className="mono">{tally.explicit_unknown}</td>
                    <td className="mono">{tally.blank}</td>
                    <td>
                      {topValue} <span className="count">({topCount})</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>手元で個票を見る</h2>
        <p>
          個票は取得器で手元に作る。リポジトリには入っていない
          (<Link href="/licenses">出典と権利</Link>)。
        </p>
        <pre className="scroll-x">
          <code>{`python -m pipeline.acquisition.itoigawa
python -m pipeline.build_jade_aggregate`}</code>
        </pre>
        <p>
          取得すると、上の三つの照合を含む帳簿の検査({checks.note_vs_sheets.gate}・
          {inline.gate}・{colour.gate})も走るようになる。
          生ファイルが無い環境では、それらは <strong>skip</strong> される ——
          「検査していない」を「合格」に見せないためである。
        </p>
      </section>
    </div>
  );
}
