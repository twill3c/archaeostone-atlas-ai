import jadePrefecturesJson from "@/public/data/jade_prefectures.json";
import areaDocumentsJson from "@/public/data/area_documents.json";
import { JADE } from "./jade";

/**
 * 地図に載せる二つの層の元データ(F-06 / F-07)。
 *
 * どちらもサーバ側(地図の頁)で必要な分だけに絞り、props で地図へ渡す ——
 * ヒスイ集計の JSON をクライアントの束に丸ごと入れないため(N-01)。
 */

interface JadePrefectureRecord {
  id: string;
  name_ja: string;
  sheet: string;
  latitude: number;
  longitude: number;
  position_meaning: string;
  scope_note: string | null;
}

export interface JadePrefectureLabel {
  id: string;
  name_ja: string;
  sheet: string;
  latitude: number;
  longitude: number;
  /** 集成表の行数(出土の記録の数)。点数ではない。 */
  rows: number;
  /** 点数が数値で入っている行。0 なら点数は**不明**であって 0 点ではない。 */
  rows_with_count: number;
  recorded_pieces: number;
  scope_note: string | null;
}

const JADE_PREFECTURES = jadePrefecturesJson as unknown as {
  note: string;
  prefectures: JadePrefectureRecord[];
};

/** 札の位置が何を意味するか(出土地点ではない)。 */
export const JADE_POSITION_NOTE = JADE_PREFECTURES.note;

/**
 * 県の札と、集成表のシートごとの件数を突き合わせる。
 *
 * **シート名で突き合わせる。** 県名で突き合わせると新潟を落とす
 * (シート名は「新潟県（上・中越）」)。見つからなければ落ちる。
 */
export function jadePrefectureLabels(): JadePrefectureLabel[] {
  const sheets = new Map(JADE.coverage.per_sheet.map((sheet) => [sheet.sheet, sheet]));
  return JADE_PREFECTURES.prefectures.map((pref) => {
    const sheet = sheets.get(pref.sheet);
    if (!sheet) throw new Error(`集成表にシート「${pref.sheet}」が無い`);
    return {
      id: pref.id,
      name_ja: pref.name_ja,
      sheet: pref.sheet,
      latitude: pref.latitude,
      longitude: pref.longitude,
      rows: sheet.rows,
      rows_with_count: sheet.rows_with_count,
      recorded_pieces: sheet.recorded_pieces,
      scope_note: pref.scope_note,
    };
  });
}

export interface AreaMunicipality {
  code: string;
  name: string;
  prefecture: string;
  parent_city_code: string | null;
  matched_codes: string[];
}

export interface AreaDocuments {
  id: string;
  municipality: AreaMunicipality | null;
  municipality_reason: string | null;
  /** 市町村が決まらなければ null(0 ではない)。 */
  documents: number | null;
  documents_by_code: Record<string, number> | null;
  obsidian_title_count: number | null;
  obsidian_titles: { title: string; url: string | null }[];
}

const AREA_DOCUMENTS = areaDocumentsJson as unknown as {
  scope: string;
  areas: AreaDocuments[];
};

export const AREA_DOCUMENTS_SCOPE = AREA_DOCUMENTS.scope;

export function areaDocumentsById(): Record<string, AreaDocuments> {
  return Object.fromEntries(AREA_DOCUMENTS.areas.map((area) => [area.id, area]));
}
