"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { geologyColour, type SourceArea } from "@/lib/data/atlas";
import { clusterBounds, clusterByScreenDistance } from "@/lib/cluster";

/**
 * 地理院の底図に GSJ の地質図を重ね、黒曜石原産地を置く。
 *
 * タイルの座標の並びが**源によって違う**ので、そこだけは取り違えないように
 * 明示しておく。地理院は `{z}/{x}/{y}`、GSJ は `{z}/{y}/{x}` である。
 * 取り違えても地図は描画され、**違う場所の地質が静かに重なる**。
 */
const GSI_PALE_TILES = "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png";
const GSJ_GEOLOGY_TILES =
  "https://gbank.gsj.jp/seamless/v2/api/1.3.1/tiles/{z}/{y}/{x}.png";

const GSI_ATTRIBUTION =
  '<a href="https://www.gsi.go.jp/" target="_blank" rel="noreferrer">出典:国土地理院ウェブサイト</a>';
const GSJ_ATTRIBUTION =
  "20万分の1日本シームレス地質図V2(&copy;産総研地質調査総合センター)";

const LEGEND_GROUPS = ["火成岩", "堆積岩", "付加体", "変成岩"] as const;

/**
 * この画面距離(px)以内の標はまとめる。
 *
 * 標の見かけは 15px なので、それより近いと互いのクリックを遮る。
 * 余裕を持たせて 22px にしてある。
 */
const CLUSTER_THRESHOLD_PX = 22;

interface Props {
  sourceAreas: SourceArea[];
}

export default function AtlasMap({ sourceAreas }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [geologyVisible, setGeologyVisible] = useState(true);
  const [geologyOpacity, setGeologyOpacity] = useState(0.55);
  const [selected, setSelected] = useState<SourceArea | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (map.current || !container.current) return;

    const instance = new maplibregl.Map({
      container: container.current,
      style: {
        version: 8,
        sources: {
          gsi: {
            type: "raster",
            tiles: [GSI_PALE_TILES],
            tileSize: 256,
            maxzoom: 18,
            attribution: GSI_ATTRIBUTION,
          },
          gsj: {
            type: "raster",
            tiles: [GSJ_GEOLOGY_TILES],
            tileSize: 256,
            maxzoom: 13,
            attribution: GSJ_ATTRIBUTION,
          },
        },
        layers: [
          { id: "gsi-base", type: "raster", source: "gsi" },
          {
            id: "gsj-geology",
            type: "raster",
            source: "gsj",
            paint: { "raster-opacity": 0.55 },
          },
        ],
      },
      center: [138.5, 37.0],
      zoom: 4.4,
      minZoom: 3,
      maxZoom: 15,
    });

    instance.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    instance.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }));

    // **`load` を待たない。** `load` は「スタイル + 初回タイル」の両方を待つので、
    // 底図の取得が失敗すると発火せず、標を一つも置かないまま終わる
    // (実測 2026-09-09: 外部タイルを遮ると標が 0 個になった)。
    // 標は DOM のオーバーレイでタイルを必要としない —— 回線が細い利用者には
    // 「底図も標も出ない」ではなく「底図が遅いが標は出る」であるべきである。
    instance.once("styledata", () => setReady(true));
    map.current = instance;

    return () => {
      instance.remove();
      map.current = null;
    };
  }, []);

  // 原産地の標。座標が確定しているものだけを置く。
  //
  // **近接する点はまとめる。** 実測(2026-09-09)では初期ズーム 4.4 で
  // 星ヶ塔・星糞峠・和田峠・東餅屋・冷山 の 5 件が重なり、互いのクリックを
  // 遮って押せなくなっていた。要素数の検査も座標の重複の検査もこれを捕まえない。
  // 位置をずらして見せることはしない —— ずらすと地図が嘘をつく。
  useEffect(() => {
    if (!ready || !map.current) return;
    const instance = map.current;
    let markers: maplibregl.Marker[] = [];

    const render = () => {
      markers.forEach((marker) => marker.remove());
      markers = [];

      const clusters = clusterByScreenDistance(
        sourceAreas,
        (lngLat) => instance.project(lngLat),
        CLUSTER_THRESHOLD_PX,
      );

      for (const cluster of clusters) {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "map-pin";

        if (cluster.members.length === 1) {
          const area = cluster.members[0];
          element.classList.add(
            area.coordinate_precision === "area" ? "map-pin--area" : "map-pin--point",
          );
          element.style.setProperty("--pin-colour", geologyColour(area.geology_group_ja));
          element.setAttribute("aria-label", `${area.name_ja} の詳細を開く`);
          element.title = `${area.name_ja}(${area.geology_group_ja ?? "地質なし"})`;
          element.addEventListener("click", (event) => {
            event.stopPropagation();
            setSelected(area);
          });
        } else {
          // 群。件数を出し、押すとその群に寄る(ズームを上げれば自然に分かれる)。
          element.classList.add("map-pin--cluster");
          element.textContent = String(cluster.members.length);
          const names = cluster.members.map((m) => m.name_ja).join("・");
          element.setAttribute(
            "aria-label",
            `${cluster.members.length} 件の原産地(${names})に寄る`,
          );
          element.title = `${cluster.members.length} 件: ${names}`;
          element.addEventListener("click", (event) => {
            event.stopPropagation();
            instance.fitBounds(clusterBounds(cluster), { padding: 90, maxZoom: 12 });
          });
        }

        markers.push(
          new maplibregl.Marker({ element, anchor: "center" })
            .setLngLat([cluster.longitude, cluster.latitude])
            .addTo(instance),
        );
      }
    };

    render();
    instance.on("moveend", render);
    instance.on("zoomend", render);

    return () => {
      instance.off("moveend", render);
      instance.off("zoomend", render);
      markers.forEach((marker) => marker.remove());
    };
  }, [ready, sourceAreas]);

  useEffect(() => {
    if (!ready || !map.current) return;
    map.current.setLayoutProperty(
      "gsj-geology",
      "visibility",
      geologyVisible ? "visible" : "none",
    );
  }, [ready, geologyVisible]);

  useEffect(() => {
    if (!ready || !map.current) return;
    map.current.setPaintProperty("gsj-geology", "raster-opacity", geologyOpacity);
  }, [ready, geologyOpacity]);

  return (
    <div className="atlas-map">
      <div className="atlas-map__controls panel">
        <h2>レイヤー</h2>
        <label className="control-row">
          <input
            type="checkbox"
            checked={geologyVisible}
            onChange={(event) => setGeologyVisible(event.target.checked)}
          />
          <span>地質図(GSJ シームレス V2)</span>
        </label>
        <label className="control-row control-row--stacked">
          <span>
            地質図の濃さ{" "}
            <span className="mono">{Math.round(geologyOpacity * 100)}%</span>
          </span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={geologyOpacity}
            disabled={!geologyVisible}
            onChange={(event) => setGeologyOpacity(Number(event.target.value))}
          />
        </label>

        <h2>凡例</h2>
        <ul className="legend">
          {LEGEND_GROUPS.map((group) => (
            <li key={group}>
              <span
                className="legend__swatch"
                style={{ background: geologyColour(group) }}
                aria-hidden="true"
              />
              {group}
            </li>
          ))}
          <li>
            <span
              className="legend__swatch legend__swatch--square"
              aria-hidden="true"
            />
            四角い標は<strong>位置が概略</strong>の原産地
          </li>
        </ul>
        <p className="legend__note">
          標の色は<strong>足もとの地質の大分類</strong>である。
          一覧と根拠は「原産地」の頁にある。
        </p>
      </div>

      <div className="atlas-map__canvas" ref={container} />

      {selected && (
        <aside className="atlas-map__panel panel" aria-label="選択した原産地">
          <button
            type="button"
            className="atlas-map__close"
            onClick={() => setSelected(null)}
            aria-label="閉じる"
          >
            ×
          </button>
          <StonePassport area={selected} />
        </aside>
      )}
    </div>
  );
}

function StonePassport({ area }: { area: SourceArea }) {
  const provenance = area.coordinate_provenance;
  return (
    <div className="passport">
      <h3>{area.name_ja}</h3>
      {area.group_ja && <p className="passport__group">{area.group_ja}</p>}

      <dl>
        <dt>石材</dt>
        <dd>黒曜石</dd>

        <dt>足もとの地質</dt>
        <dd>
          {area.geology_group_ja ? (
            <>
              <strong>{area.geology_group_ja}</strong> — {area.lithology_ja}
            </>
          ) : (
            <span className="passport__absent">
              図郭にポリゴンが無い(内水面・海岸など)
            </span>
          )}
        </dd>

        <dt>形成年代</dt>
        <dd>{area.formation_age_ja ?? "—"}</dd>

        <dt>座標</dt>
        <dd className="mono">
          {area.latitude?.toFixed(5)}, {area.longitude?.toFixed(5)}
          {area.coordinate_precision === "area" && (
            <span className="badge badge--no">位置は概略</span>
          )}
        </dd>

        <dt>座標の出所</dt>
        <dd>
          国土地理院 地名検索に「{provenance.query}」で問い合わせ、
          {provenance.candidate_count} 件の候補のうち{" "}
          <strong>{(provenance.candidate_index ?? 0) + 1} 番目</strong>「
          {provenance.candidate_title}」を採った。
          <br />
          <span className="passport__rule">規則: {provenance.rule}</span>
        </dd>

        <dt>根拠の種別</dt>
        <dd>
          <span className="ev-chip" style={{ color: "var(--ev-c)" }}>
            Level C 本アトラスの整理
          </span>
        </dd>

        <dt>典拠</dt>
        <dd>
          <ul className="passport__citations">
            {area.citations.map((citation) => (
              <li key={citation.citation_id}>
                <a href={citation.url} target="_blank" rel="noreferrer">
                  {citation.title}
                </a>
              </li>
            ))}
          </ul>
        </dd>
      </dl>

      {area.note && <p className="passport__note">{area.note}</p>}
    </div>
  );
}
