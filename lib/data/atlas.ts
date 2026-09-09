import sourceAreasJson from "@/public/data/source_areas.json";
import geologyStatsJson from "@/public/data/geology_stats.json";

export interface Citation {
  citation_id: string;
  title: string;
  url: string;
  source_id: string;
}

export interface CoordinateProvenance {
  method: string;
  query: string;
  candidate_count: number;
  candidate_index: number | null;
  candidate_title: string | null;
  rule: string | null;
  rule_kind: string;
  outcome: string;
}

export interface SourceArea {
  id: string;
  source_id: string;
  material_id: string;
  name_ja: string;
  group_ja: string | null;
  prefecture_code: string | null;
  latitude: number | null;
  longitude: number | null;
  coordinate_precision: "point" | "area";
  coordinate_provenance: CoordinateProvenance;
  evidence_status: "curated" | "needs_review";
  note: string | null;
  citations: Citation[];
  geology_outcome: string | null;
  geology_symbol: string | null;
  formation_age_ja: string | null;
  formation_age_en: string | null;
  geology_group_ja: string | null;
  geology_group_en: string | null;
  lithology_ja: string | null;
  lithology_en: string | null;
}

export interface SourceAreaPayload {
  generated_by: string;
  counts: {
    total: number;
    resolved: number;
    needs_review: number;
    with_geology: number;
    coordinate_precision_area: number;
  };
  coverage_note: string;
  source_areas: SourceArea[];
}

export const SOURCE_AREAS = sourceAreasJson as unknown as SourceAreaPayload;

export interface VariantResult {
  target: string;
  source_n: number;
  control_n: number;
  source_proportion: number | null;
  control_proportion: number | null;
  observed_difference: number | null;
  p_value: number | null;
  iterations: number;
  seed: number;
  reason: string | null;
}

export interface Claim {
  claim_id: string;
  statement: string;
  /** 「成立」「不成立」「検定不可」。**測って落ちた主張も載せる。** */
  verdict: string;
  verdict_note: string;
  variants: Record<string, VariantResult>;
}

export interface GeologyStats {
  generated_by: string;
  method: {
    test: string;
    iterations: number;
    seed: number;
    alpha: number;
    verdict_rule: string;
    control_group: string;
    non_circularity: string;
    limitation: string;
  };
  distributions: {
    source_areas: {
      group_ja: Record<string, number>;
      lithology_ja: Record<string, number>;
      n: number;
      n_measured: number;
    };
    control_points: {
      group_ja: Record<string, number>;
      lithology_ja: Record<string, number>;
      n: number;
      n_measured: number;
    };
  };
  claims: Claim[];
}

export const GEOLOGY_STATS = geologyStatsJson as unknown as GeologyStats;

/** 地図に置ける原産地(座標が確定しているもの)。 */
export function mappableSourceAreas(): SourceArea[] {
  return SOURCE_AREAS.source_areas.filter(
    (area) => area.latitude !== null && area.longitude !== null,
  );
}

export function sourceAreaById(id: string): SourceArea | undefined {
  return SOURCE_AREAS.source_areas.find((area) => area.id === id);
}

/**
 * 地質の大分類に対応する色。
 *
 * **色だけに依存させない**(構想書 §9.3)。地図では記号の形も変え、
 * 一覧では大分類の文字を必ず併記する。
 */
export const GEOLOGY_GROUP_COLOURS: Record<string, string> = {
  火成岩: "#c1440e",
  堆積岩: "#c8a24a",
  付加体: "#4a7c59",
  変成岩: "#4a6fa5",
  その他: "#7a7a7a",
};

export function geologyColour(group: string | null): string {
  if (group === null) return "#9a9a9a";
  return GEOLOGY_GROUP_COLOURS[group] ?? "#9a9a9a";
}
