import licenses from "@/public/data/licenses.json";

export interface SourceLicense {
  source_id: string;
  title: string;
  source_url: string;
  license_url: string;
  license_name: string;
  license_quote: string;
  redistribution: boolean;
  redistribution_reason: string | null;
  modification: boolean;
  attribution_required: boolean;
  attribution_text: string | null;
  verified_at: string;
}

export interface Attribution {
  source_id: string;
  text: string;
  url: string;
}

export interface LicensesPayload {
  generated_from: string;
  counts: { total: number; redistributable: number; not_redistributable: number };
  attributions: Attribution[];
  sources: SourceLicense[];
}

export const LICENSES = licenses as unknown as LicensesPayload;

/** 出典表示が要る源(常時表示する — 構想書 §36)。 */
export function attributions(): Attribution[] {
  return LICENSES.attributions;
}

/** 配ってよい源だけ。 */
export function redistributableSources(): SourceLicense[] {
  return LICENSES.sources.filter((s) => s.redistribution);
}

/** 配れない源。**隠さずに理由ごと出す**(SPEC §2.1)。 */
export function restrictedSources(): SourceLicense[] {
  return LICENSES.sources.filter((s) => !s.redistribution);
}
