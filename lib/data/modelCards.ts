import cardsJson from "@/public/data/model_cards.json";

export interface Counts {
  balanced_accuracy: number;
  tp: number;
  fn: number;
  fp: number;
  tn: number;
}

export interface G10Verdict {
  verdict: string;
  difference: number;
  margin: number;
  distinguishable: boolean;
  permutation_p: number;
  resolution_per_positive: number;
  rule: string;
}

export interface LikenessCard {
  model_id: "provenance-likeness-logistic";
  task: string;
  status: string;
  trained: boolean;
  ui_enabled: boolean;
  framework: string;
  features: string[];
  training_data: string[];
  split: string;
  summary: string;
  metrics: {
    n_positive: number;
    n_negative: number;
    n_groups: number;
    majority: Counts;
    rule: Counts & { selected_rule_counts: Record<string, number> };
    logistic: Counts & {
      pooled_auc: number | null;
      permutation: { n: number; mean: number | null; max: number | null; p: number | null; seed: number | null };
    };
  };
  g10: G10Verdict;
  limitations: string[];
}

export interface XrfCard {
  model_id: "obsidian-provenance-xrf";
  task: string;
  status: "no_go";
  trained: false;
  ui_enabled: false;
  summary: string;
  go_criteria: { name: string; met: boolean; evidence: string }[];
  no_go_triggers: {
    name: string;
    triggered: boolean | null;
    evidence: string;
    instruments_seen?: string[];
  }[];
  method_reference: string;
  limitations: string[];
}

interface CardsPayload {
  generated_by: string;
  cards: (LikenessCard | XrfCard)[];
}

const PAYLOAD = cardsJson as unknown as CardsPayload;

export function likenessCard(): LikenessCard {
  const card = PAYLOAD.cards.find((c) => c.model_id === "provenance-likeness-logistic");
  if (!card) throw new Error("原産地らしさのモデルカードが無い");
  return card as LikenessCard;
}

export function xrfCard(): XrfCard {
  const card = PAYLOAD.cards.find((c) => c.model_id === "obsidian-provenance-xrf");
  if (!card) throw new Error("蛍光X線のモデルカードが無い");
  return card as XrfCard;
}

/** 特徴名を画面用の日本語へ。 */
export const FEATURE_LABELS: Record<string, string> = {
  "group_火成岩": "大分類が火成岩",
  "group_堆積岩": "大分類が堆積岩",
  "group_付加体": "大分類が付加体",
  "group_変成岩": "大分類が変成岩",
  "group_その他": "大分類がその他",
  "era_第四紀": "年代が第四紀",
  "era_新第三紀": "年代が新第三紀",
  "era_古第三紀": "年代が古第三紀",
  "era_白亜紀": "年代が白亜紀",
  "era_それ以前": "年代が白亜紀より前",
  felsic: "岩相が珪長質(流紋岩・デイサイト)",
  volcanic: "岩相が火山岩(溶岩・火砕岩)",
  plutonic: "岩相が深成岩(花崗岩・閃緑岩など)",
  unconsolidated: "未固結の堆積物",
};
