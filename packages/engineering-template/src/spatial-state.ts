/** Protected deterministic geometry and causal graph state; no clock, IO or mutable simulation. */
import type { SpatialSpec } from './semantic-types';
export const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
export const smooth = (value: number) => {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
};
export function seeded(seed: number, index: number) {
  let x = Math.imul(seed ^ (index + 1), 0x45d9f3b);
  x = Math.imul(x ^ (x >>> 16), 0x45d9f3b);
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
}
export function cityBuildings(spec: SpatialSpec) {
  const result: {
    id: string;
    x: number;
    z: number;
    width: number;
    depth: number;
    height: number;
    color: string;
  }[] = [];
  for (let i = 0; result.length < spec.count && i < spec.count * 3; i++) {
    const col = i % spec.columns,
      row = Math.floor(i / spec.columns);
    const x = (col - (spec.columns - 1) / 2) * 2.25;
    const z = (row - Math.ceil(spec.count / spec.columns) / 2) * 2.25;
    const core = Math.exp(-(x * x + z * z) / 130);
    result.push({
      id: `building-${i}`,
      x,
      z,
      width: 0.85 + seeded(spec.seed, i * 4) * 0.72,
      depth: 0.85 + seeded(spec.seed, i * 4 + 1) * 0.75,
      height: 0.65 + seeded(spec.seed, i * 4 + 2) * (2.2 + 10 * core),
      color: seeded(spec.seed, i * 4 + 3) > 0.64 ? '#9edbdf' : '#e6adc7',
    });
  }
  return result;
}
export function cameraPose(spec: SpatialSpec, progress: number) {
  const angle = 0.72 + (clamp01(progress) * spec.orbit_degrees * Math.PI) / 180;
  return {
    position: [
      Math.sin(angle) * spec.camera_radius,
      spec.camera_height,
      Math.cos(angle) * spec.camera_radius,
    ] as [number, number, number],
    target: [0, 1.1, 0] as [number, number, number],
  };
}
export function matrixState(count: number, progress: number) {
  const p = clamp01(progress);
  return { progress: p, visible: Math.floor(p * count + 1e-9), total: count };
}
export function networkGeometry(spec: SpatialSpec, progress: number) {
  const p = clamp01(progress),
    n = spec.count,
    columns = Math.min(spec.columns, n);
  const nodes = Array.from({ length: n }, (_, i) => {
    const col = i % columns,
      row = Math.floor(i / columns),
      rows = Math.ceil(n / columns);
    const ax = 0.31 + (col * 0.38) / Math.max(1, columns - 1),
      ay = 0.32 + (row * 0.28) / Math.max(1, rows - 1);
    const bx =
      0.08 + (col * 0.84) / Math.max(1, columns - 1) + (seeded(spec.seed, i * 2) - 0.5) * 0.065;
    const by =
      0.2 + (row * 0.68) / Math.max(1, rows - 1) + (seeded(spec.seed, i * 2 + 1) - 0.5) * 0.08;
    return { id: `node-${i}`, index: i, x: ax + (bx - ax) * p, y: ay + (by - ay) * p };
  });
  const edges: { id: string; from: number; to: number }[] = [];
  const keys = new Set<string>();
  for (let i = 0; i < n; i++)
    for (const to of [(i + 1) % n, (i + columns) % n]) {
      const a = Math.min(i, to),
        b = Math.max(i, to),
        key = `${a}-${b}`;
      if (a !== b && !keys.has(key)) {
        keys.add(key);
        edges.push({ id: key, from: a, to: b });
      }
    }
  return { nodes, edges };
}
export function graphHops(spec: SpatialSpec) {
  const { edges } = networkGeometry(spec, 0),
    hops = Array(spec.count).fill(Infinity);
  const queue = [spec.source_node];
  hops[spec.source_node] = 0;
  for (let i = 0; i < queue.length; i++) {
    const a = queue[i];
    for (const edge of edges) {
      const b = edge.from === a ? edge.to : edge.to === a ? edge.from : -1;
      if (b >= 0 && !Number.isFinite(hops[b])) {
        hops[b] = hops[a] + 1;
        queue.push(b);
      }
    }
  }
  return hops as number[];
}
export function propagationState(spec: SpatialSpec, progress: number) {
  const hops = graphHops(spec),
    max = Math.max(...hops),
    p = clamp01(progress);
  const reached = hops.map((hop) => p > 0 && hop <= p * max + 1e-8);
  return { hops, reached, count: reached.filter(Boolean).length, wave: p * max };
}
