/** Execute only fixed repository-owned pure render modules; never takes source/path arguments. */
const fs = require('node:fs'),
  path = require('node:path'),
  assert = require('node:assert/strict');
const Module = require('node:module'),
  ts = require('typescript'),
  React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const root = path.resolve(__dirname, '../packages/engineering-template/src'),
  cache = new Map();
const allowed = new Set(['theme', 'code-view', 'mechanism-kit', 'semantic-kit', 'scene-objects']);
function load(name) {
  assert(allowed.has(name));
  if (cache.has(name)) return cache.get(name).exports;
  const filename = path.join(root, name + '.tsx');
  const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.React,
      esModuleInterop: true,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const module = new Module(filename);
  module.filename = filename;
  module.paths = Module._nodeModulePaths(root);
  cache.set(name, module);
  module.require = (request) =>
    request.startsWith('./') ? load(request.slice(2)) : require(request);
  module._compile(source, filename);
  return module.exports;
}
const { codeRows, codeViewport } = load('code-view');
const text = 'x'.repeat(135) + '最后必须完整显示';
assert.equal(
  codeRows(text)
    .map((x) => x.text)
    .join(''),
  text,
);
const code = Array.from({ length: 24 }, (_, i) =>
  i === 23 ? 'important_fix_must_be_seen()' : `line_${i + 1}()`,
).join('\n');
const scene = { code, motion: { code_focus: [] }, compiled_events: [] };
assert(
  codeViewport(scene, 300, 1).rows.some(
    (row) => row.line === 24 && row.text.includes('important_fix'),
  ),
);
const focus = {
  ...scene,
  motion: { code_focus: [{ element_id: 'issue', line: 24 }] },
  compiled_events: [{ target: 'issue', start_frame: 20, end_frame: 40 }],
};
assert.equal(codeViewport(focus, 30, 0.1).binding.line, 24);
assert(codeViewport(focus, 30, 0.1).rows.some((x) => x.line === 24));
const { parameterValue, flowState, MechanismPanel } = load('mechanism-kit');
const parameter = { id: 'level', minimum: 0, maximum: 1, initial: 0, unit: '' };
const mechanisms = {
  semantic_scene: { parameters: [parameter] },
  compiled_semantic_events: [
    { target: 'level', action: 'parameter', value: 1, start_frame: 30, end_frame: 60 },
  ],
};
assert.equal(parameterValue(mechanisms, 'level', 0), 0);
assert.equal(parameterValue(mechanisms, 'level', 60), 1);
assert.equal(parameterValue(mechanisms, 'level', 45), 0.5);
const entity = {
  id: 'dial',
  component: 'Dial',
  title: '强度',
  parameter_id: 'level',
  width: 600,
  height: 400,
};
const markup = (f) =>
  renderToStaticMarkup(
    React.createElement(MechanismPanel, { scene: mechanisms, entity, frame: f }),
  );
assert.notEqual(markup(0), markup(60));
const tree = (f) =>
  renderToStaticMarkup(
    React.createElement(MechanismPanel, {
      scene: mechanisms,
      entity: { ...entity, component: 'BranchTree' },
      frame: f,
    }),
  );
assert(tree(60).split('<circle').length > tree(0).split('<circle').length);
const flow = {
  semantic_scene: {
    parameters: [
      { id: 'stock', minimum: 0, maximum: 100, initial: 5 },
      { id: 'in', minimum: 0, maximum: 100, initial: 10 },
      { id: 'out', minimum: 0, maximum: 100, initial: 2 },
    ],
  },
  compiled_semantic_events: [],
};
const tank = {
  id: 'tank',
  parameter_id: 'stock',
  inflow_id: 'in',
  outflow_id: 'out',
  capacity: 20,
};
const state = flowState(flow, tank, 300);
assert(
  Math.abs(state.stock - 20) < 1e-8 &&
    Math.abs(state.processed - 20) < 1e-8 &&
    Math.abs(state.overflow - 65) < 1e-8,
);
assert(Math.abs(state.stock + state.processed + state.overflow - 5 - state.arrived) < 1e-8);
assert.equal(flowState(flow, tank, 0).stock, 5);
const { ThemeProvider, designPacks } = load('theme'),
  { SemanticPanel } = load('semantic-kit');
const e = {
  id: 'task',
  component: 'TaskState',
  title: '任务',
  state: 'pending',
  items: [{ text: '结果', detail: '', active: false }],
  text: '',
  width: 520,
  height: 300,
};
const themed = (pack) =>
  renderToStaticMarkup(
    React.createElement(
      ThemeProvider,
      { pack },
      React.createElement(SemanticPanel, {
        scene: { compiled_semantic_events: [] },
        entity: e,
        frame: 0,
        width: 520,
        height: 300,
      }),
    ),
  );
assert.notEqual(themed('editorial_warm'), themed('workspace_tech'));
assert(themed('editorial_warm').includes(designPacks.editorial_warm.header));
console.log(
  'Visual contracts passed: full code preservation/pages/focus, shared parameter linkage, stock conservation/capacity, semantic themes.',
);

for (const component of ['Dial', 'BranchTree', 'MetricBar']) {
  const output = renderToStaticMarkup(
    React.createElement(MechanismPanel, {
      scene: mechanisms,
      entity: { ...entity, component },
      frame: 60,
    }),
  );
  assert(output.includes(`data-mechanism="${component}"`));
}
for (const component of ['FlowReservoir', 'QueueFlow']) {
  const e = {
    ...entity,
    id: component,
    component,
    parameter_id: 'stock',
    inflow_id: 'in',
    outflow_id: 'out',
    capacity: 20,
  };
  const f = flowState(flow, e, 300);
  assert(Math.abs(f.stock + f.processed + f.overflow - (5 + f.arrived)) < 1e-7);
  assert(f.overflow > 0 && f.stock === 20);
  assert(
    renderToStaticMarkup(
      React.createElement(MechanismPanel, { scene: flow, entity: e, frame: 300 }),
    ).includes('data-stock="20"'),
  );
}

const range = {
  ...scene,
  motion: { code_focus: [{ element_id: 'issue', line: 1, end_line: 24 }] },
  compiled_events: [{ target: 'issue', start_frame: 0, end_frame: 100 }],
};
assert(codeViewport(range, 0, 0).rows.some((x) => x.line === 1));
assert(codeViewport(range, 100, 0).rows.some((x) => x.line === 24));
