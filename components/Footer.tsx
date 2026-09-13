/**
 * フリート共通フッタ(koho-lens 準拠・5 項目・この並び・下部固定)。T-406/T-407 が固定する。
 *
 * 公開前の実測(2026-09-14)で、ここは三つとも規約から外れていた。
 * - GitHub が存在しないアカウント、App Menu が 404 の別名を指していた(T-400/T-401)
 * - ライセンスの項目が <span> で、リンクですらなかった。© は項目の文言に含めず直後の地の文にする
 * - 解説アーティファクトの 2 本が null で、項目ごと隠れていた
 *
 * 区切りの「・」は文字で置く —— CSS の ::before で描くと innerText に出ず、検品から見えない。
 * App Menu の本番は app-menu-amber。接尾辞の無い app-menu の vercel ドメインは他者の別サービス。
 */
const LICENSE_URL = "https://github.com/twill3c/archaeostone-atlas-ai/blob/main/LICENSE";
const GITHUB_URL = "https://github.com/twill3c/archaeostone-atlas-ai";
const GUIDE_URL = "https://claude.ai/code/artifact/e0bf220e-dd2b-48a8-9740-61cc7ebe5a8a";
const BLUEPRINT_URL = "https://claude.ai/code/artifact/174be22e-70c4-48af-9df9-116917c7525d";
const APP_MENU_URL = "https://app-menu-amber.vercel.app/";

export default function Footer() {
  return (
    <footer className="fleet-footer">
      <a href={LICENSE_URL} target="_blank" rel="noreferrer">
        MIT License
      </a>
      <span>© 2026 坂田哲朗</span>
      <span aria-hidden="true">・</span>
      <a href={GITHUB_URL} target="_blank" rel="noreferrer">
        GitHub
      </a>
      <span aria-hidden="true">・</span>
      <a href={GUIDE_URL} target="_blank" rel="noreferrer">
        石材アトラスの歩き方
      </a>
      <span aria-hidden="true">・</span>
      <a href={BLUEPRINT_URL} target="_blank" rel="noreferrer">
        石材アトラスの設計図
      </a>
      <span aria-hidden="true">・</span>
      <a href={APP_MENU_URL} target="_blank" rel="noreferrer">
        App Menu
      </a>
    </footer>
  );
}
