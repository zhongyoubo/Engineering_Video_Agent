/** Trusted, data-only AI visual vocabulary. Custom authoring still uses isolation. */
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { ObjectScene } from './scene-objects';
import type { Scene } from './contracts';
import type { SemanticEntity, SemanticState } from './semantic-types';
const labels: Record<SemanticState, string> = {
  pending: '待执行',
  running: '执行中',
  succeeded: '已完成',
  failed: '失败',
  awaiting_confirmation: '等待确认',
  rejected: '已拒绝',
  cancelled: '已取消',
};
const tone = (s: SemanticState) =>
  s === 'failed' || s === 'rejected'
    ? '#b85759'
    : s === 'awaiting_confirmation'
      ? '#b37b25'
      : '#098b82';
export function semanticState(scene: Scene, entity: SemanticEntity, frame: number) {
  const result = { ...entity, items: entity.items.map((i) => ({ ...i })), highlight: false };
  for (const event of scene.compiled_semantic_events || []) {
    if (event.target !== entity.id) continue;
    if (event.action === 'highlight' && frame >= event.start_frame && frame < event.end_frame)
      result.highlight = true;
    if (frame < event.end_frame) continue;
    if (event.to_state) result.state = event.to_state;
    if (event.action === 'append') {
      result.text += event.text || '';
      result.items.push(...event.items.map((i) => ({ ...i })));
    } else {
      if (event.text != null) result.text = event.text;
      if (event.items.length) result.items = event.items.map((i) => ({ ...i }));
    }
    if (event.action === 'select')
      result.items = result.items.map((item, i) => ({ ...item, active: i === event.selected }));
  }
  return result;
}
export function SemanticPanel({
  scene,
  entity,
  frame,
  width,
  height,
  assets = {},
}: {
  scene: Scene;
  entity: SemanticEntity;
  frame: number;
  width: number;
  height: number;
  assets?: Record<string, string>;
}) {
  const e = semanticState(scene, entity, frame),
    color = tone(e.state),
    small = width < 300;
  const n = small ? Math.max(12, Math.min(18, width / 12)) : 24;
  const pad = small ? 10 : 22;
  const showState =
    ['PromptInput', 'ToolCall', 'TaskState', 'ApprovalGate', 'CodeWorkspace'].includes(
      e.component,
    ) || e.state !== 'pending';
  const row = (text: string, detail: string, active: boolean, i: number) => (
    <div
      key={i}
      style={{
        padding: small ? '6px 8px' : '10px 14px',
        marginBottom: 7,
        borderRadius: 8,
        background: active ? '#d8eee4' : '#f1f4ef',
        borderLeft: `${active ? 5 : 2}px solid ${active ? color : '#cbd8d3'}`,
      }}
    >
      <div>{text}</div>
      {detail && <div style={{ fontSize: n * 0.76, color: '#587272', marginTop: 3 }}>{detail}</div>}
    </div>
  );
  let content: React.ReactNode;
  switch (e.component) {
    case 'AssetImage': {
      const src = e.asset_key && assets[e.asset_key];
      content = src ? (
        <Img
          src={staticFile(src)}
          style={{ width: '100%', height: '100%', objectFit: 'contain', objectPosition: 'top' }}
        />
      ) : (
        <div style={{ color: '#a04a4a' }}>素材待制作</div>
      );
      break;
    }
    case 'TokenSequence':
      content = (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {e.items.map((i, k) => (
            <span
              key={k}
              style={{
                padding: '9px 12px',
                background: i.active ? '#d6a35d' : '#dceae4',
                borderRadius: 6,
                borderBottom: '3px solid #779f98',
              }}
            >
              {i.text}
            </span>
          ))}
        </div>
      );
      break;
    case 'Conversation':
      content = (
        <div>
          {e.items.map((i, k) => (
            <div
              key={k}
              style={{
                marginLeft: k % 2 ? 0 : width * 0.12,
                marginRight: k % 2 ? width * 0.12 : 0,
                background: k % 2 ? '#fff' : '#dcefe6',
                padding: 10,
                borderRadius: 14,
                marginBottom: 12,
              }}
            >
              <div>{i.text}</div>
              <div style={{ fontSize: n * 0.75, color: '#55716e' }}>{i.detail}</div>
            </div>
          ))}
        </div>
      );
      break;
    case 'ModelBoundary':
      content = (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1 }}>
            {e.items.slice(0, 2).map((i, k) => row(i.text, i.detail, i.active, k))}
          </div>
          <div
            style={{
              border: `4px solid ${color}`,
              borderRadius: '50%',
              width: small ? 50 : 100,
              height: small ? 50 : 100,
              display: 'grid',
              placeItems: 'center',
              background: '#e1eee9',
              flexShrink: 0,
            }}
          >
            模型
          </div>
          <div style={{ flex: 1 }}>
            {e.items.slice(2).map((i, k) => row(i.text, i.detail, i.active, k))}
          </div>
        </div>
      );
      break;
    case 'ContextWindow':
      content = (
        <div style={{ border: '2px dashed #80aaa0', borderRadius: 10, padding: 10 }}>
          {e.items.map((i, k) => row(i.text, i.detail, i.active, k))}
          <div style={{ height: 9, background: '#d9e3dd', borderRadius: 5, overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: Math.min(100, (e.items.length / 12) * 100) + '%',
                background: color,
              }}
            />
          </div>
        </div>
      );
      break;
    case 'DocumentChunks':
      content = (
        <div style={{ borderLeft: '8px solid #d3c2a0', paddingLeft: 12 }}>
          {e.items.map((i, k) => (
            <div
              key={k}
              style={{
                marginBottom: 10,
                padding: 12,
                background: i.active ? '#fff0bc' : '#fff',
                borderBottom: '2px solid #d9e2da',
                boxShadow: '3px 3px 0 #d7e1dc',
              }}
            >
              {i.text}
              <div style={{ fontSize: n * 0.75, color: '#607a76' }}>{i.detail}</div>
            </div>
          ))}
        </div>
      );
      break;
    case 'RetrievalResults':
      content = (
        <div>
          {e.items.map((i, k) => (
            <div
              key={k}
              style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}
            >
              <b style={{ color: i.active ? color : '#8da8a1', fontSize: n * 1.3 }}>{k + 1}</b>
              <div style={{ flex: 1 }}>{row(i.text, i.detail, i.active, k)}</div>
            </div>
          ))}
        </div>
      );
      break;
    case 'CodeWorkspace':
      content = (
        <div
          style={{
            background: '#16323c',
            color: '#d9eee6',
            padding: 12,
            borderRadius: 8,
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            fontSize: n * 0.85,
          }}
        >
          {e.items.map((i, k) => (
            <div key={k} style={{ background: i.active ? '#275b50' : 'transparent', padding: 3 }}>
              <span style={{ color: '#91b2a7', marginRight: 10 }}>{k + 1}</span>
              {i.text}
              {i.detail && <div style={{ color: '#dcb774' }}>{i.detail}</div>}
            </div>
          ))}
        </div>
      );
      break;
    case 'TaskState':
      content = (
        <div>
          {e.items.map((i, k) => (
            <div
              key={k}
              style={{ display: 'flex', gap: 12, marginBottom: 10, alignItems: 'center' }}
            >
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  background: i.active ? color : '#cbdad3',
                  display: 'inline-block',
                }}
              />
              <div>
                <div>{i.text}</div>
                <div style={{ fontSize: n * 0.75, color: '#5e7774' }}>{i.detail}</div>
              </div>
            </div>
          ))}
        </div>
      );
      break;
    case 'ToolCall':
      content = (
        <>
          <div
            style={{
              fontFamily: 'monospace',
              background: '#173d44',
              color: '#dcece5',
              padding: 10,
              borderRadius: 8,
              fontSize: n * 0.8,
            }}
          >
            {e.items[0]?.text || 'request'}
            <div style={{ color: '#a4c6b9' }}>{e.items[0]?.detail}</div>
          </div>
          <div style={{ margin: '8px 0', color }}>↓ {labels[e.state]}</div>
          {e.items.slice(1).map((i, k) => row(i.text, i.detail, i.active, k))}
        </>
      );
      break;
    default:
      content = <>{e.items.map((i, k) => row(i.text, i.detail, i.active, k))}</>;
  }
  return (
    <div
      data-semantic-entity={entity.id}
      data-state={e.state}
      style={{
        width,
        height,
        boxSizing: 'border-box',
        background: '#fffdf7',
        border: `${e.highlight ? 4 : 2}px solid ${e.highlight ? '#d4a052' : '#bad2c7'}`,
        borderRadius: small ? 8 : 18,
        overflow: 'hidden',
        color: '#193f43',
        fontSize: n,
        lineHeight: 1.35,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          padding: small ? '7px 9px' : '12px 18px',
          background: '#173f43',
          color: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          gap: 5,
          fontSize: small ? n : n + 3,
        }}
      >
        <span>{e.title}</span>
        {showState && e.state === 'running' && (
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            style={{ flexShrink: 0, transform: `rotate(${frame * 6}deg)` }}
          >
            <circle
              cx="10"
              cy="10"
              r="7"
              fill="none"
              stroke="#8fe1c4"
              strokeWidth="3"
              strokeDasharray="25 20"
            />
          </svg>
        )}
        {showState && (
          <span style={{ fontSize: n * 0.7, whiteSpace: 'nowrap', color: '#bddbd0' }}>
            {labels[e.state]}
          </span>
        )}
      </div>
      <div style={{ padding: pad, overflow: 'hidden', flex: 1 }}>
        {e.text && (
          <div
            style={{
              marginBottom: 10,
              whiteSpace: 'pre-wrap',
              fontSize: e.component === 'PromptInput' ? n * 1.15 : n,
            }}
          >
            {e.text}
          </div>
        )}
        {content}
      </div>
      {(e.component === 'ApprovalGate' || e.component === 'PromptInput') && (
        <div
          style={{
            margin: pad,
            marginTop: 0,
            padding: small ? 6 : 10,
            borderRadius: 8,
            background: color,
            color: '#fff',
            textAlign: 'center',
          }}
        >
          {e.component === 'ApprovalGate'
            ? labels[e.state]
            : e.state === 'pending'
              ? '提交目标'
              : labels[e.state]}
        </div>
      )}
      {e.component === 'EvidenceStack' && (
        <div style={{ padding: '4px 12px', fontSize: n * 0.65, color: '#687f74' }}>
          {e.provenance === 'observed' ? '有记录的依据' : '教学示例依据'}
        </div>
      )}
    </div>
  );
}
export function SceneRenderer({
  scene,
  assets = {},
  frameOverride,
  titleOverride,
}: {
  scene: Scene;
  assets?: Record<string, string>;
  frameOverride?: number;
  titleOverride?: string;
}) {
  const now = useCurrentFrame(),
    frame = frameOverride ?? now;
  const entities = scene.semantic_scene?.entities || [];
  const renderScreen = (o: { id: string }, f: number, w: number, h: number) => {
    const e = entities.find((e) => e.bind_to === o.id);
    return e ? (
      <SemanticPanel scene={scene} entity={e} frame={f} width={w} height={h} assets={assets} />
    ) : null;
  };
  const label = (o: { id: string; label: string }) => {
    const e = entities.find((e) => e.bind_to === o.id);
    return e ? e.title + ' · ' + labels[semanticState(scene, e, frame).state] : o.label;
  };
  return (
    <AbsoluteFill style={{ background: '#edf4f4', color: '#173f43' }}>
      {scene.visual_scene ? (
        <ObjectScene
          scene={scene}
          frameOverride={frame}
          titleOverride={titleOverride}
          renderScreen={renderScreen}
          objectLabel={label}
        />
      ) : (
        <>
          <div
            style={{
              position: 'absolute',
              left: 100,
              top: 65,
              fontSize: titleOverride ? 64 : 48,
              fontWeight: 750,
            }}
          >
            {titleOverride || scene.title}
          </div>
          <div
            style={{ position: 'absolute', left: 100, top: 158, fontSize: 22, color: '#66857d' }}
          >
            {scene.semantic_scene?.viewer_question}
          </div>
        </>
      )}
      <div style={{ position: 'absolute', left: 100, top: 220, width: 1720, height: 650 }}>
        {entities
          .filter((e) => !e.bind_to)
          .map((e) => (
            <div key={e.id} style={{ position: 'absolute', left: e.x, top: e.y }}>
              <SemanticPanel
                scene={scene}
                entity={e}
                frame={frame}
                width={e.width}
                height={e.height}
                assets={assets}
              />
            </div>
          ))}
      </div>
    </AbsoluteFill>
  );
}
