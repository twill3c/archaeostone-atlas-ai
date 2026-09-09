/**
 * 画面上のまとめ方の検査(T-110〜 / G-14 の前提)。
 *
 * これは見せ方の検査ではない。**重なった標は互いのクリックを遮って押せなくなる**
 * (実測 2026-09-09)。だから「重なりが残っていないこと」を測る。
 *
 * 投影は替え玉で与える。実測ではメルカトルだが、まとめ方の性質は投影に依らない ——
 * 依らないことをここで固定しておくと、地図の実装を替えても検査が生き残る。
 */

import { describe, expect, it } from "vitest";
import {
  clusterByScreenDistance,
  clusterBounds,
  type Project,
} from "../lib/cluster";

/** 経度 1 度 = 10px、緯度 1 度 = 10px の単純な投影(南が下)。 */
const linear: Project = ([lon, lat]) => ({ x: lon * 10, y: -lat * 10 });

const pt = (name: string, lat: number, lon: number) => ({
  name,
  latitude: lat,
  longitude: lon,
});

describe("clusterByScreenDistance", () => {
  it("T-110: 離れた点はまとまらない", () => {
    const items = [pt("a", 0, 0), pt("b", 0, 10), pt("c", 0, 20)];
    const clusters = clusterByScreenDistance(items, linear, 20);
    expect(clusters).toHaveLength(3);
    expect(clusters.every((c) => c.members.length === 1)).toBe(true);
  });

  it("T-111: 近い点はまとまる", () => {
    const items = [pt("a", 0, 0), pt("b", 0, 1), pt("c", 0, 2)];
    const clusters = clusterByScreenDistance(items, linear, 20);
    expect(clusters).toHaveLength(1);
    expect(clusters[0].members.map((m) => m.name)).toEqual(["a", "b", "c"]);
  });

  it("T-112: 座標を持たない点は落とす(推測で置かない)", () => {
    const items = [
      pt("a", 0, 0),
      { name: "none", latitude: null, longitude: null },
    ];
    const clusters = clusterByScreenDistance(items, linear, 20);
    expect(clusters).toHaveLength(1);
    expect(clusters[0].members.map((m) => m.name)).toEqual(["a"]);
  });

  it("T-113: 入力の順序に依らず同じ群になる", () => {
    // 貪欲な逐次割り当てだと順序で結果が変わる。連結成分なら変わらない。
    const items = [pt("a", 0, 0), pt("b", 0, 1.5), pt("c", 0, 3)];
    const forward = clusterByScreenDistance(items, linear, 20);
    const backward = clusterByScreenDistance([...items].reverse(), linear, 20);

    const names = <T extends { name: string }>(cs: { members: T[] }[]) =>
      cs.map((c) => c.members.map((m) => m.name).sort().join("+")).sort();

    expect(names(forward)).toEqual(names(backward));
  });

  it("T-114(陽性対照): まとめないと重なりが残ることを示す", () => {
    // この対照が無いと、T-115 は「たまたま重なりが無かった」でも緑になる。
    const items = [pt("a", 0, 0), pt("b", 0, 0.2), pt("c", 0, 0.4)];
    const unclustered = clusterByScreenDistance(items, linear, 0);
    expect(unclustered).toHaveLength(3);

    // 閾値 0 では、点どうしの画面距離が標の大きさより近い組が実在する。
    const PIN_PX = 15;
    let overlapping = 0;
    for (let i = 0; i < unclustered.length; i += 1) {
      for (let j = i + 1; j < unclustered.length; j += 1) {
        const a = linear([unclustered[i].longitude, unclustered[i].latitude]);
        const b = linear([unclustered[j].longitude, unclustered[j].latitude]);
        if (Math.hypot(a.x - b.x, a.y - b.y) < PIN_PX) overlapping += 1;
      }
    }
    expect(overlapping).toBeGreaterThan(0);
  });

  it("T-115: まとめた後は、群どうしが標の大きさより近くならない", () => {
    const items = [
      pt("a", 0, 0),
      pt("b", 0, 0.2),
      pt("c", 0, 0.4),
      pt("far", 0, 30),
    ];
    const PIN_PX = 15;
    const clusters = clusterByScreenDistance(items, linear, PIN_PX);

    for (let i = 0; i < clusters.length; i += 1) {
      for (let j = i + 1; j < clusters.length; j += 1) {
        const a = linear([clusters[i].longitude, clusters[i].latitude]);
        const b = linear([clusters[j].longitude, clusters[j].latitude]);
        expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThanOrEqual(PIN_PX);
      }
    }
  });

  it("T-116: 群の代表位置は構成員の重心で、位置を動かさない", () => {
    // 見やすさのために点をずらすことはしない —— ずらすと地図が嘘をつく。
    const items = [pt("a", 10, 20), pt("b", 12, 24)];
    const [cluster] = clusterByScreenDistance(items, linear, 1000);
    expect(cluster.latitude).toBe(11);
    expect(cluster.longitude).toBe(22);
  });

  it("T-117: 全件がどこかの群に一度だけ属する(取りこぼしと重複が無い)", () => {
    const items = Array.from({ length: 30 }, (_, i) =>
      pt(`p${i}`, (i % 7) * 0.3, Math.floor(i / 7) * 0.3),
    );
    const clusters = clusterByScreenDistance(items, linear, 12);
    const seen = clusters.flatMap((c) => c.members.map((m) => m.name));
    expect(seen).toHaveLength(items.length);
    expect(new Set(seen).size).toBe(items.length);
  });
});

describe("clusterBounds", () => {
  it("T-118: 群を囲む矩形が全構成員を含む", () => {
    const items = [pt("a", 10, 20), pt("b", 12, 24), pt("c", 11, 19)];
    const [cluster] = clusterByScreenDistance(items, linear, 1000);
    const [[west, south], [east, north]] = clusterBounds(cluster);

    for (const member of cluster.members) {
      expect(member.longitude).toBeGreaterThanOrEqual(west);
      expect(member.longitude).toBeLessThanOrEqual(east);
      expect(member.latitude).toBeGreaterThanOrEqual(south);
      expect(member.latitude).toBeLessThanOrEqual(north);
    }
  });
});
