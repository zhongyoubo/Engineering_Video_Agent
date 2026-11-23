/** Protected parameter mechanisms. Rates/stock are illustrative, never invented observations. */
import React from 'react';
import type { Scene } from './contracts';
import type { SemanticEntity } from './semantic-types';
import { useTheme } from './theme';
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export function parameterValue(scene: Scene, id: string, frame: number) {
  const p = scene.semantic_scene?.parameters?.find((p) => p.id === id);
  if (!p) throw new Error('Unknown mechanism parameter');
  let result = p.initial;
  for (const event of scene.compiled_semantic_events || []) {
    if (event.action !== 'parameter' || event.target !== id || frame < event.start_frame) continue;
    const t = clamp((frame - event.start_frame) / (event.end_frame - event.start_frame));
    const ease = t * t * (3 - 2 * t);
    result += ((event.value ?? result) - result) * ease;
  }
  return result;
}
type Stock = { stock: number; arrived: number; processed: number; overflow: number };
const history = new WeakMap<Scene, Map<string, Stock[]>>();
export function flowState(scene: Scene, entity: SemanticEntity, frame: number): Stock {
  let map = history.get(scene);
  if (!map) {
    map = new Map();
    history.set(scene, map);
  }
  let states = map.get(entity.id);
  if (!states) {
    states = [
      {
        stock: parameterValue(scene, entity.parameter_id!, 0),
        arrived: 0,
        processed: 0,
        overflow: 0,
      },
    ];
    map.set(entity.id, states);
  }
  const fps = 30;
  const capacity = entity.capacity || 100;
  for (let f = states.length; f <= Math.max(0, Math.floor(frame)); f++) {
    const prev = states[f - 1],
      incoming = parameterValue(scene, entity.inflow_id!, f - 1) / fps;
    const outgoing = Math.min(
      prev.stock + incoming,
      parameterValue(scene, entity.outflow_id!, f - 1) / fps,
    );
    const uncapped = prev.stock + incoming - outgoing,
      overflow = Math.max(0, uncapped - capacity);
    states.push({
      stock: Math.min(capacity, Math.max(0, uncapped)),
      arrived: prev.arrived + incoming,
      processed: prev.processed + outgoing,
      overflow: prev.overflow + overflow,
    });
  }
  return states[Math.max(0, Math.floor(frame))];
}
export function MechanismPanel({
  scene,
  entity,
  frame,
}: {
  scene: Scene;
  entity: SemanticEntity;
  frame: number;
}) {
  const theme = useTheme(),
    parameter = scene.semantic_scene?.parameters?.find((p) => p.id === entity.parameter_id);
  if (!parameter) throw new Error('Unknown mechanism binding');
  const value = parameterValue(scene, parameter.id, frame),
    ratio = clamp((value - parameter.minimum) / (parameter.maximum - parameter.minimum));
  const flow = ['FlowReservoir', 'QueueFlow'].includes(entity.component)
    ? flowState(scene, entity, frame)
    : null;
  const formatted = (x: number) => Number(x.toFixed(1));
  let body: React.ReactNode;
  if (entity.component === 'Dial') {
    const angle = ((-135 + 270 * ratio) * Math.PI) / 180;
    body = (
      <>
        <circle
          cx="300"
          cy="170"
          r="100"
          fill={theme.panel}
          stroke={theme.border}
          strokeWidth="8"
        />
        {Array.from({ length: 13 }, (_, i) => {
          const a = ((-135 + i * 22.5) * Math.PI) / 180;
          return (
            <line
              key={i}
              x1={300 + 80 * Math.sin(a)}
              y1={170 - 80 * Math.cos(a)}
              x2={300 + 93 * Math.sin(a)}
              y2={170 - 93 * Math.cos(a)}
              stroke={theme.muted}
              strokeWidth="3"
            />
          );
        })}
        <line
          x1="300"
          y1="170"
          x2={300 + 75 * Math.sin(angle)}
          y2={170 - 75 * Math.cos(angle)}
          stroke={theme.accent}
          strokeWidth="8"
          strokeLinecap="round"
        />
        <circle cx="300" cy="170" r="10" fill={theme.ink} />
        <text x="300" y="320" textAnchor="middle">
          {formatted(value)} {parameter.unit}
        </text>
      </>
    );
  } else if (entity.component === 'BranchTree') {
    const depth = 1 + Math.floor(ratio * 3),
      edges: React.ReactNode[] = [];
    const branch = (x: number, y: number, level: number, span: number) => {
      if (level === depth) return;
      for (const sign of [-1, 1]) {
        const nx = x + 105,
          ny = y + sign * span;
        edges.push(
          <path
            key={edges.length}
            d={`M${x} ${y} C${x + 50} ${y},${nx - 50} ${ny},${nx} ${ny}`}
            fill="none"
            stroke={theme.accent}
            strokeWidth="3"
          />,
        );
        edges.push(
          <circle key={edges.length} cx={nx} cy={ny} r="5" fill={theme.panel} stroke={theme.ink} />,
        );
        branch(nx, ny, level + 1, span / 2);
      }
    };
    branch(60, 185, 0, 72);
    body = (
      <>
        {edges}
        <circle cx="60" cy="185" r="9" fill={theme.ink} />
        <text x="300" y="330" textAnchor="middle">{`展开 ${depth} 层`}</text>
      </>
    );
  } else if (entity.component === 'MetricBar') {
    body = (
      <>
        <rect x="60" y="160" width="480" height="35" rx="12" fill={theme.soft} />
        <rect x="60" y="160" width={480 * ratio} height="35" rx="12" fill={theme.accent} />
        <text x="60" y="245">
          {formatted(value)} {parameter.unit}
        </text>
      </>
    );
  } else if (flow && entity.component === 'FlowReservoir') {
    const level = flow.stock / (entity.capacity || 100);
    body = (
      <>
        <path
          d="M210 80 V300 Q210 315 225 315 H375 Q390 315 390 300 V80"
          fill={theme.panel}
          stroke={theme.ink}
          strokeWidth="6"
        />
        <rect
          x="216"
          y={305 - 215 * level}
          width="168"
          height={215 * level}
          fill={theme.accent}
          opacity=".65"
        />
        <path
          d="M80 65 H300 V95 M285 80 L300 95 L315 80 M390 280 H480 L465 265 M480 280 L465 295"
          fill="none"
          stroke={theme.accent}
          strokeWidth="4"
        />
        <text x="45" y="50">
          流入 {formatted(parameterValue(scene, entity.inflow_id!, frame))}/秒
        </text>
        <text x="402" y="330">
          流出 {formatted(parameterValue(scene, entity.outflow_id!, frame))}/秒
        </text>
        <text x="300" y="365" textAnchor="middle">
          存量 {formatted(flow.stock)}
        </text>
      </>
    );
  } else if (flow) {
    const n = Math.min(24, Math.ceil(flow.stock));
    body = (
      <>
        <rect x="410" y="105" width="140" height="160" rx="12" fill={theme.header} />
        <text x="480" y="193" textAnchor="middle" fill={theme.headerText}>
          处理器
        </text>
        <path d="M45 185 H390" stroke={theme.border} strokeWidth="5" />
        {Array.from({ length: n }, (_, i) => (
          <rect
            key={i}
            x={65 + (i % 8) * 40}
            y={110 + Math.floor(i / 8) * 45}
            width="27"
            height="27"
            rx="5"
            fill={theme.accent}
          />
        ))}
        <text
          x="45"
          y="310"
        >{`等待 ${formatted(flow.stock)} · 已处理 ${formatted(flow.processed)}`}</text>
        <text
          x="45"
          y="355"
          fill={flow.overflow > 0 ? theme.danger : theme.muted}
        >{`超出容量 ${formatted(flow.overflow)}`}</text>
      </>
    );
  }
  return (
    <svg
      data-mechanism={entity.component}
      data-parameter-value={value}
      data-stock={flow?.stock}
      width={entity.width}
      height={entity.height}
      viewBox="0 0 600 400"
      style={{ overflow: 'visible', color: theme.ink }}
      fontFamily="inherit"
      fontSize="22"
      fill={theme.ink}
    >
      <text x="25" y="28" fontSize="27" fontWeight="700">
        {entity.title}
      </text>
      {body}
    </svg>
  );
}
