import documentsJson from "@/public/data/documents.json";

export interface MaterialMention {
  hits: number;
  rate: number | null;
  terms: string[];
  examples: { title: string; url: string | null; prefecture_codes: string[] }[];
}

export interface DocumentsPayload {
  generated_by: string;
  source_id: string;
  corpus: {
    pages_parsed: number;
    records: number;
    records_with_metadata: number;
    record_shapes: Record<string, number>;
    records_without_set_spec: number;
    set_spec_kinds: Record<string, number>;
  };
  material_mentions: {
    scope: string;
    denominator: number;
    counts: Record<string, MaterialMention>;
    method_terms: Record<string, number>;
    note: string;
  };
  by_prefecture: { code: string; name: string; documents: number }[];
  municipality_count: number;
  top_municipalities: { code: string; documents: number }[];
}

export const DOCUMENTS = documentsJson as unknown as DocumentsPayload;

/** 材質キー → 日本語の見出し。画面で使う。 */
export const MATERIAL_LABELS: Record<string, string> = {
  obsidian: "黒曜石",
  jadeite: "ヒスイ",
  sanukite: "サヌカイト",
  chert: "チャート",
  jasper: "碧玉",
  agate: "瑪瑙",
  serpentinite: "蛇紋岩",
  quartz: "水晶",
};

/** 件数の多い順。 */
export function materialMentionsRanked(): [string, MaterialMention][] {
  return Object.entries(DOCUMENTS.material_mentions.counts).sort(
    (a, b) => b[1].hits - a[1].hits,
  );
}

/** 源の公表値と、実際に数えた件数の差。 */
export const COMPLETE_LIST_SIZE = 312_794;
