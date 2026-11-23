/** Trusted, data-only AI visual vocabulary. Custom authoring still uses isolation. */
import React, { useEffect, useLayoutEffect, useState } from 'react';
type SpatialPanelProps = React.ComponentProps<typeof import('./spatial-kit').default>;
function SpatialPanel(props: SpatialPanelProps) {
  const [loaded, setLoaded] = useState<{
    Component: typeof import('./spatial-kit').default;
  } | null>(null);
  const [handle] = useState(() => delayRender('protected spatial renderer mounted'));
  useEffect(() => {
    let active = true;
    import('./spatial-kit')
      .then((module) => {
        if (active) setLoaded({ Component: module.default });
      })
      .catch(cancelRender);
    return () => {
      active = false;
      continueRender(handle);
    };
  }, [handle]);
  // Resolving the import alone does not guarantee React has committed its visual subtree.
  useLayoutEffect(() => {
    if (loaded) continueRender(handle);
  }, [loaded, handle]);
  return loaded ? <loaded.Component {...props} /> : null;
}
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  delayRender,
  continueRender,
  cancelRender,
} from 'remotion';
import { MechanismPanel } from './mechanism-kit';
import { ObjectScene } from './scene-objects';
import type { Scene } from './contracts';
import { useTheme, ThemeProvider } from './theme';
import type { DesignPack, ThemeTokens } from './theme';
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
const tone = (s: SemanticState, theme: ThemeTokens) =>
  s === 'failed' || s === 'rejected'
    ? theme.danger
    : s === 'awaiting_confirmation'
      ? theme.warning
      : theme.success;
export function semanticState(scene: Scene, entity: SemanticEntity, frame: number) {
  const result = {
    opacity: 1,
    scale: 1,
    rotation: 0,
    ...entity,
    items: entity.items.map((i) => ({ ...i })),
    highlight: false,
  };
  for (const event of scene.compiled_semantic_events || []) {
    if (event.target !== entity.id) continue;
    if (event.action === 'highlight' && frame >= event.start_frame && frame < event.end_frame)
      result.highlight = true;
    if (event.action === 'transform') {
      const progress = Math.max(
        0,
        Math.min(1, (frame - event.start_frame) / (event.end_frame - event.start_frame)),
      );
      const t = progress * progress * (3 - 2 * progress);
      for (const key of ['x', 'y', 'opacity', 'scale', 'rotation'] as const) {
        const dest = event[key];
        if (dest != null) result[key] = result[key] + (dest - result[key]) * t;
      }
      continue;
    }
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
  const theme = useTheme();
  const e = semanticState(scene, entity, frame),
    color = tone(e.state, theme),
    small = width < 300;
  const n = small ? Math.max(12, Math.min(18, width / 12)) : 24;
  const pad = small ? 10 : 22;
  const showState =
    ['PromptInput', 'ToolCall', 'TaskState', 'ApprovalGate', 'CodeWorkspace'].includes(
      e.component,
    ) || e.state !== 'pending';
  if (['SpatialCity', 'QuantityMatrix', 'NodeNetwork'].includes(e.component)) {
    return (
      <SpatialPanel
        scene={scene}
        entity={e}
        frame={frame}
        width={width}
        height={height}
        assets={assets}
      />
    );
  }
  if (['Dial', 'BranchTree', 'MetricBar', 'FlowReservoir', 'QueueFlow'].includes(e.component)) {
    return <MechanismPanel scene={scene} entity={e} frame={frame} />;
  }
  const row = (text: string, detail: string, active: boolean, i: number) => (
    <div
      key={i}
      style={{
        padding: small ? '6px 8px' : '10px 14px',
        marginBottom: 7,
        borderRadius: 8,
        background: active ? theme.selected : theme.soft,
        borderLeft: `${active ? 5 : 2}px solid ${active ? color : theme.border}`,
      }}
    >
      <div>{text}</div>
      {detail && (
        <div style={{ fontSize: n * 0.76, color: theme.muted, marginTop: 3 }}>{detail}</div>
      )}
    </div>
  );
  if (e.component === 'AssetImage' && e.image_style === 'artwork') {
    const src = e.asset_key && assets[e.asset_key];
    if (!src) throw new Error('Unregistered artwork asset');
    return (
      <Img
        data-semantic-entity={e.id}
        src={staticFile(src)}
        style={{ width, height, objectFit: e.image_fit || 'contain' }}
      />
    );
  }
  let content: React.ReactNode;
  switch (e.component) {
    case 'AssetImage': {
      const src = e.asset_key && assets[e.asset_key];
      content = src ? (
        <Img
          src={staticFile(src)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: e.image_fit || 'contain',
            objectPosition: 'top',
          }}
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
                background: i.active ? theme.accent : theme.soft,
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
                background: k % 2 ? theme.panel : theme.selected,
                padding: 10,
                borderRadius: 14,
                marginBottom: 12,
              }}
            >
              <div>{i.text}</div>
              <div style={{ fontSize: n * 0.75, color: theme.muted }}>{i.detail}</div>
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
              background: theme.soft,
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
          <div style={{ height: 9, background: theme.soft, borderRadius: 5, overflow: 'hidden' }}>
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
                background: i.active ? theme.selected : theme.panel,
                borderBottom: '2px solid #d9e2da',
                boxShadow: '3px 3px 0 #d7e1dc',
              }}
            >
              {i.text}
              <div style={{ fontSize: n * 0.75, color: theme.muted }}>{i.detail}</div>
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
              <b style={{ color: i.active ? color : theme.muted, fontSize: n * 1.3 }}>{k + 1}</b>
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
            background: theme.code,
            color: theme.codeText,
            padding: 12,
            borderRadius: 8,
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap',
            fontSize: n * 0.85,
          }}
        >
          {e.items.map((i, k) => (
            <div
              key={k}
              style={{ background: i.active ? theme.selected : 'transparent', padding: 3 }}
            >
              <span style={{ color: theme.muted, marginRight: 10 }}>{k + 1}</span>
              {i.text}
              {i.detail && <div style={{ color: theme.warning }}>{i.detail}</div>}
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
                  background: i.active ? color : theme.border,
                  display: 'inline-block',
                }}
              />
              <div>
                <div>{i.text}</div>
                <div style={{ fontSize: n * 0.75, color: theme.muted }}>{i.detail}</div>
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
              background: theme.code,
              color: theme.codeText,
              padding: 10,
              borderRadius: 8,
              fontSize: n * 0.8,
            }}
          >
            {e.items[0]?.text || 'request'}
            <div style={{ color: theme.muted }}>{e.items[0]?.detail}</div>
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
        background: theme.panel,
        border: `${e.highlight ? 4 : 2}px solid ${e.highlight ? theme.accent : theme.border}`,
        borderRadius: small ? 8 : 18,
        overflow: 'hidden',
        color: theme.ink,
        fontSize: n,
        lineHeight: 1.35,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          padding: small ? '7px 9px' : '12px 18px',
          background: theme.header,
          color: theme.panel,
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
          <span style={{ fontSize: n * 0.7, whiteSpace: 'nowrap', color: theme.headerText }}>
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
            color: theme.panel,
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
      {e.component === 'EvidenceStack' && e.provenance === 'observed' && (
        <div style={{ padding: '4px 12px', fontSize: n * 0.65, color: theme.muted }}>
          有记录的依据
        </div>
      )}
    </div>
  );
}
function SceneContent({
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
  const theme = useTheme();
  const now = useCurrentFrame(),
    frame = frameOverride ?? now;
  const entities = scene.semantic_scene?.entities || [];
  const art = scene.semantic_scene;
  const bg = art?.background_asset_key && assets[art.background_asset_key];
  if (art?.background_asset_key && !bg) throw new Error('Unregistered background asset');
  const renderScreen = (o: { id: string }, f: number, w: number, h: number) => {
    const e = entities.find((e) => e.bind_to === o.id);
    return e ? (
      <div style={{ width: w, height: h, opacity: semanticState(scene, e, f).opacity }}>
        <SemanticPanel scene={scene} entity={e} frame={f} width={w} height={h} assets={assets} />
      </div>
    ) : null;
  };
  const label = (o: { id: string; label: string }) => {
    const e = entities.find((e) => e.bind_to === o.id);
    return e ? e.title + ' · ' + labels[semanticState(scene, e, frame).state] : o.label;
  };
  return (
    <AbsoluteFill
      style={{
        background: art?.background_color || theme.background,
        color: art?.title_color || theme.ink,
      }}
    >
      {bg && (
        <Img
          src={staticFile(bg)}
          style={{ position: 'absolute', width: '100%', height: '100%', objectFit: 'cover' }}
        />
      )}
      {scene.visual_scene ? (
        <ObjectScene
          scene={scene}
          frameOverride={frame}
          titleOverride={titleOverride}
          renderScreen={renderScreen}
          objectLabel={label}
          transparentBackground={Boolean(bg)}
        />
      ) : art?.show_heading !== false ? (
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
            style={{ position: 'absolute', left: 100, top: 158, fontSize: 22, color: theme.muted }}
          >
            {scene.semantic_scene?.viewer_question}
          </div>
        </>
      ) : null}
      <div
        style={{
          position: 'absolute',
          left: entities.some((e) => e.immersive) ? 0 : 100,
          top: entities.some((e) => e.immersive) ? 0 : 220,
          width: entities.some((e) => e.immersive) ? 1920 : 1720,
          height: entities.some((e) => e.immersive) ? 1080 : 650,
        }}
      >
        {entities
          .filter((e) => !e.bind_to)
          .map((entity) => {
            const e = semanticState(scene, entity, frame);
            return (
              <div
                key={e.id}
                style={{
                  position: 'absolute',
                  left: e.x,
                  top: e.y,
                  opacity: e.opacity,
                  transform: `scale(${e.scale}) rotate(${e.rotation}deg)`,
                  transformOrigin: 'center',
                }}
              >
                <SemanticPanel
                  scene={scene}
                  entity={entity}
                  frame={frame}
                  width={e.width}
                  height={e.height}
                  assets={assets}
                />
              </div>
            );
          })}
      </div>
    </AbsoluteFill>
  );
}

export function SceneRenderer(
  props: React.ComponentProps<typeof SceneContent> & { designPack?: DesignPack },
) {
  return props.designPack ? (
    <ThemeProvider pack={props.designPack}>
      <SceneContent {...props} />
    </ThemeProvider>
  ) : (
    <SceneContent {...props} />
  );
}
