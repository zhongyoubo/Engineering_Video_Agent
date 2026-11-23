/** ONLY fixed protected platform code; no arbitrary source/path inputs or native inference. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const { pathToFileURL } = require('node:url');
const root = path.resolve(__dirname, '../packages/engineering-template');
const file = path.join(root, 'src/creative-kit.ts');
const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleFixture = new Module(file);
moduleFixture._compile(compiled, file);
const { creativeProgress, registeredMaterial } = moduleFixture.exports;
const scene = {
  start_frame: 100,
  frames: 360,
  compiled_creative_events: [{ id: 'open', start_frame: 220, end_frame: 280 }],
};
assert.equal(creativeProgress(scene, 'open', 0), 0);
assert.equal(creativeProgress(scene, 'open', 250), 0.5);
assert.equal(creativeProgress(scene, 'open', 359), 1);
assert.throws(() => creativeProgress(scene, 'absent', 20));
assert.throws(() => registeredMaterial({}, 'missing'));
assert.equal(registeredMaterial({ book: 'generated/hash.png' }, 'book'), 'generated/hash.png');
(async () => {
  const { requiresWebGL } = await import(pathToFileURL(path.join(root, 'render-capabilities.mjs')));
  assert(requiresWebGL({ scenes: [{ creation: { techniques: ['three'] } }] }));
  assert(!requiresWebGL({ scenes: [{ creation: { techniques: ['svg', 'images'] } }] }));
  assert(
    requiresWebGL({ scenes: [{ semantic_scene: { entities: [{ component: 'SpatialCity' }] } }] }),
  );
  const { reviewWindows, causalFrames } = await import(
    pathToFileURL(path.join(root, 'review-plan.mjs'))
  );
  assert.deepEqual(causalFrames(scene), [319, 350, 381]);
  assert(reviewWindows(scene, 30).some((w) => w.start <= 319 && w.end >= 381));
  console.log(
    'Creative contracts passed: generic 3D activation, free causal progress, held results, late-event review and registered assets.',
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
