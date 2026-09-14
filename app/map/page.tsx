import type { Metadata } from "next";
import AtlasMap from "@/components/AtlasMap";
import { SOURCE_AREAS, mappableSourceAreas } from "@/lib/data/atlas";
import {
  AREA_DOCUMENTS_SCOPE,
  JADE_POSITION_NOTE,
  areaDocumentsById,
  jadePrefectureLabels,
} from "@/lib/data/mapLayers";

export const metadata: Metadata = {
  title: "地図",
  description:
    "地理院の淡色地図に産総研シームレス地質図を重ね、典拠つきの黒曜石原産地と県別のヒスイ集計を置く。",
};

export default function MapPage() {
  const areas = mappableSourceAreas();
  const { counts } = SOURCE_AREAS;

  return (
    <div className="map-page">
      <header className="map-page__head">
        <h1>地図</h1>
        <p className="lede">
          地理院の淡色地図に産総研の 20 万分の 1 シームレス地質図を重ね、
          黒曜石原産地 {areas.length} 件を置いた。標をクリックすると、
          座標の出所・典拠・その市町村の報告書まで辿れる。
        </p>
        {counts.needs_review > 0 && (
          <p className="notice">
            座標が確定していない原産地 {counts.needs_review} 件は地図に載せていない。
            <strong>推測で置かない。</strong>
          </p>
        )}
      </header>

      <AtlasMap
        sourceAreas={areas}
        jadeLabels={jadePrefectureLabels()}
        jadePositionNote={JADE_POSITION_NOTE}
        areaDocuments={areaDocumentsById()}
        documentsScope={AREA_DOCUMENTS_SCOPE}
      />
    </div>
  );
}
