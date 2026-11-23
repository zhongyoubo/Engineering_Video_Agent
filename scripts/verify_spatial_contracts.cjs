/** Pure platform geometry only. Hardcoded filename; no arbitrary source/path inputs. */
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  path = require('node:path'),
  ts = require('typescript'),
  Module = require('node:module');
const file = path.resolve(__dirname, '../packages/engineering-template/src/spatial-state.ts');
const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const target = new Module(file);
target.filename = file;
target._compile(compiled, file);
const { cityBuildings, cameraPose, matrixState, networkGeometry, propagationState } =
  target.exports;
const spec = {
  seed: 17,
  count: 48,
  columns: 8,
  camera_radius: 34,
  camera_height: 18,
  orbit_degrees: 36,
  source_node: 0,
  asset_keys: [],
};
assert.deepEqual(cityBuildings(spec), cityBuildings(spec));
assert.notDeepEqual(cityBuildings(spec), cityBuildings({ ...spec, seed: 18 }));
assert.equal(new Set(cityBuildings(spec).map((b) => b.id)).size, 48);
assert.notDeepEqual(cameraPose(spec, 0), cameraPose(spec, 1));
assert.deepEqual(cameraPose(spec, -2), cameraPose(spec, 0));
for (const p of [-1, 0, 0.1, 0.5, 1, 2]) {
  const m = matrixState(240, p);
  assert(m.visible >= 0 && m.visible <= 240);
}
assert.equal(matrixState(240, 0.5).visible, 120);
const a = networkGeometry(spec, 0),
  b = networkGeometry(spec, 1);
assert.deepEqual(
  a.nodes.map((n) => n.id),
  b.nodes.map((n) => n.id),
);
assert.deepEqual(a.edges, b.edges);
assert(a.nodes.some((n, i) => n.x !== b.nodes[i].x));
for (const edge of b.edges) assert(b.nodes[edge.from] && b.nodes[edge.to]);
assert.equal(propagationState(spec, 0).count, 0);
assert.equal(propagationState(spec, 1).count, 48);
const mid = propagationState(spec, 0.35);
assert(mid.count > 0 && mid.count < 48);
for (const e of a.edges) assert(Math.abs(mid.hops[e.from] - mid.hops[e.to]) <= 1);
console.log(
  'Spatial contracts passed: deterministic geometry, camera, bounded quantity, stable node/edge identity, shortest-hop propagation.',
);
