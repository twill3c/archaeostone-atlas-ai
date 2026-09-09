import jadeJson from "@/public/data/jade_aggregate.json";

export interface SheetCoverage {
  sheet: string;
  rows: number;
  rows_with_count: number;
  recorded_pieces: number;
  columns: number;
  extra_column_count: number;
}

export interface Tally {
  distinct: number;
  recorded: number;
  /** 「不明」と明記された行。0 ではなく**不明**である。 */
  explicit_unknown: number;
  blank: number;
  top: [string, number][];
}

export interface NoteVsSheets {
  gate: string;
  description: string;
  named_in_note: string[];
  sheets: string[];
  named_but_missing: string[];
  present_but_unnamed: string[];
}

export interface InlineCheck {
  gate: string;
  description: string;
  compared: number;
  agreements: number;
  disagreements: number;
  unparsed: number;
  fullwidth_only: number;
  without_count: number;
  disagreement_notations: {
    sheet: string;
    notation: string;
    inline_total: number;
    recorded_count: number;
  }[];
}

export interface BackgroundCheck {
  gate: string;
  description: string;
  flagged_rows: number;
  blank_count_rows: number;
  match: boolean;
  sheets_with_flags: string[];
  observed_colours: number[][];
  declared_colour: number[];
  note: string;
}

export interface JadeAggregate {
  generated_by: string;
  source_id: string;
  redistribution_notice: string;
  coverage: {
    sheets: number;
    rows: number;
    rows_with_count: number;
    recorded_pieces: number;
    note: string;
    per_sheet: SheetCoverage[];
    count_cell_types: Record<string, number>;
  };
  internal_checks: {
    note_vs_sheets: NoteVsSheets;
    inline_counts_vs_count_column: InlineCheck;
    background_colour_vs_blank_cells: BackgroundCheck;
  };
  tallies: Record<string, Tally>;
}

export const JADE = jadeJson as unknown as JadeAggregate;

/** 集計の列を、画面に出す順で。 */
export const TALLY_ORDER = ["時代", "時期", "種別", "形状", "出土状況", "石材"] as const;

/** RGB の配列を CSS の色へ。 */
export function rgbToCss(rgb: number[]): string {
  const [r, g, b] = rgb;
  return `rgb(${r} ${g} ${b})`;
}
