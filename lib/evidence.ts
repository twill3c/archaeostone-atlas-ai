/**
 * 根拠の階段(Evidence Ladder) — SPEC §7 F-11 / 構想書 §31。
 *
 * このアトラスの中心にある規律は「文献の事実と AI 仮説を完全に分離する」ことである。
 * 画面に出るあらゆる主張は、必ずこの 5 段のどれかに属する。属さないものは出さない。
 *
 * **記号(色・線種)は仕様の述語に対応していなければならない**(HC-079)。
 * ここでの述語は「その主張が何に支えられているか」であって、確からしさの強弱ではない。
 */

export type EvidenceLevel = "A" | "B" | "C" | "D" | "E";

export interface EvidenceDefinition {
  level: EvidenceLevel;
  labelJa: string;
  labelEn: string;
  /** その段が支えにしているもの。ここに書けないものは、その段に置けない。 */
  basis: string;
  /** 地図上の線の描き方。色だけに依存させない(構想書 §9.3)。 */
  stroke: "solid" | "thin-solid" | "dashed" | "dotted";
  cssVar: string;
}

export const EVIDENCE_LADDER: readonly EvidenceDefinition[] = [
  {
    level: "A",
    labelJa: "公表された実測",
    labelEn: "Published measurement",
    basis: "査読・報告された機器分析の測定値(蛍光X線分析など)",
    stroke: "solid",
    cssVar: "--ev-a",
  },
  {
    level: "B",
    labelJa: "公表された記述",
    labelEn: "Published description",
    basis: "報告書・集成表に「そう書かれている」こと。同定の正否は含意しない",
    stroke: "thin-solid",
    cssVar: "--ev-b",
  },
  {
    level: "C",
    labelJa: "本アトラスの整理",
    labelEn: "Curated interpretation",
    basis: "公表された事実を、本アトラスが典拠を挙げて突き合わせ・正規化したもの",
    stroke: "thin-solid",
    cssVar: "--ev-c",
  },
  {
    level: "D",
    labelJa: "モデル推定",
    labelEn: "AI prediction",
    basis: "学習したモデルの出力。確定的な判定ではない",
    stroke: "dashed",
    cssVar: "--ev-d",
  },
  {
    level: "E",
    labelJa: "探索的仮説",
    labelEn: "Exploratory hypothesis",
    basis: "統計的な近さから引いた、確かめられていない見立て",
    stroke: "dotted",
    cssVar: "--ev-e",
  },
] as const;

const BY_LEVEL = new Map(EVIDENCE_LADDER.map((d) => [d.level, d]));

export function evidenceDefinition(level: EvidenceLevel): EvidenceDefinition {
  const found = BY_LEVEL.get(level);
  if (!found) throw new Error(`未知の根拠段: ${level}`);
  return found;
}

/**
 * AI 出力に使ってはならない語(構想書 §31.2)。
 *
 * 画面の文言を検査するために置く。**「引用・言及」と「使用・依存」を分ける**
 * ため、この配列そのものは禁止語の一覧であって違反ではない(HC-074)。
 */
export const FORBIDDEN_AI_PHRASES: readonly string[] = [
  "確定",
  "証明",
  "新発見",
  "交易路である",
] as const;

/** AI 出力に推奨される語。 */
export const PREFERRED_AI_PHRASES: readonly string[] = [
  "モデル推定",
  "類似度",
  "候補",
  "仮説レイヤー",
] as const;
