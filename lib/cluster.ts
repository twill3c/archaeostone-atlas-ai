/**
 * 近接する点を画面上でまとめる(構想書 §2.1 の「クラスタリング」)。
 *
 * これは見せ方の都合ではなく**操作できるかどうか**の問題である。
 * 実測(2026-09-09)では初期ズーム 4.4 で 星ヶ塔・星糞峠・和田峠・東餅屋・冷山 の
 * 5 件が重なり、**互いのクリックを遮って押せなくなっていた**。
 * 要素数の検査も座標の重複の検査も、この故障を捕まえない。
 *
 * まとめるのは**画面上の距離**であって地理的な距離ではない。ズームを上げれば
 * 自然に分かれる。位置を動かして見せる(オフセット)ことはしない ——
 * 動かすと地図が嘘をつく。
 */

export interface Clusterable {
  latitude: number | null;
  longitude: number | null;
}

export interface Cluster<T extends Clusterable> {
  /** この群に属する要素。1 件のときは単独の点として描く。 */
  members: T[];
  /** 群の代表位置(構成員の重心)。単独なら本人の位置。 */
  latitude: number;
  longitude: number;
}

/** 画面座標へ落とす関数。MapLibre の `project` を渡す。 */
export type Project = (lngLat: [number, number]) => { x: number; y: number };

/**
 * 画面上で `thresholdPx` 以内に集まる点をまとめる。
 *
 * 単連結成分(距離グラフの連結成分)で作る。貪欲な逐次割り当てだと
 * 入力の順序で結果が変わるので、順序に依存しない形にしてある。
 */
export function clusterByScreenDistance<T extends Clusterable>(
  items: readonly T[],
  project: Project,
  thresholdPx: number,
): Cluster<T>[] {
  const placed = items.filter(
    (item): item is T & { latitude: number; longitude: number } =>
      item.latitude !== null && item.longitude !== null,
  );
  if (placed.length === 0) return [];

  const points = placed.map((item) => project([item.longitude, item.latitude]));

  // Union-Find。連結成分なので、どの順序で見ても同じ群になる。
  const parent = placed.map((_, index) => index);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const union = (a: number, b: number) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[Math.max(ra, rb)] = Math.min(ra, rb);
  };

  const threshold2 = thresholdPx * thresholdPx;
  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      const dx = points[i].x - points[j].x;
      const dy = points[i].y - points[j].y;
      if (dx * dx + dy * dy <= threshold2) union(i, j);
    }
  }

  const groups = new Map<number, number[]>();
  for (let i = 0; i < placed.length; i += 1) {
    const root = find(i);
    groups.set(root, [...(groups.get(root) ?? []), i]);
  }

  return [...groups.values()].map((indices) => {
    const members = indices.map((i) => placed[i]);
    return {
      members,
      latitude: members.reduce((sum, m) => sum + m.latitude, 0) / members.length,
      longitude: members.reduce((sum, m) => sum + m.longitude, 0) / members.length,
    };
  });
}

/** 群を囲む矩形。押したときに寄せるために使う。 */
export function clusterBounds<T extends Clusterable>(
  cluster: Cluster<T>,
): [[number, number], [number, number]] {
  const lats = cluster.members.map((m) => m.latitude as number);
  const lons = cluster.members.map((m) => m.longitude as number);
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ];
}
