import React, { useEffect, useState } from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  continueRender,
  cancelRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type { Scene, VideoProps } from './types';
import { Bookend, ViewerDisclosures } from '../../engineering-template/src/presentation';
import { ThemeProvider, useTheme } from '../../engineering-template/src/theme';
import { SceneRenderer } from '../../engineering-template/src/semantic-kit';
import { ObjectScene, ObjectSceneSounds } from '../../engineering-template/src/scene-objects';
export type { Scene, Storyboard, VideoProps, EditorialRequest, ContentStrategy } from './types';

const colors = { blue: '#3869ef', violet: '#7953df', teal: '#087f83', amber: '#bc7620' };
const source = (path: string) =>
  path.startsWith('/') || path.startsWith('http') ? path : staticFile(path);
const reveal = (f: number, from = 0) =>
  interpolate(f, [from, from + 16], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
const Badge = ({ text, color }: { text: string; color: string }) => (
  <span
    style={{
      padding: '9px 16px',
      borderRadius: 9,
      fontSize: 17,
      color,
      background: color + '12',
      border: `1px solid ${color}25`,
    }}
  >
    {text}
  </span>
);

function Graph({ scene, color }: { scene: Scene; color: string }) {
  const f = useCurrentFrame();
  const labels = scene.bullets.length ? scene.bullets : ['INPUT', 'PROCESS', 'OUTPUT'];
  const n = Math.min(labels.length, 6),
    columns = scene.type === 'flow' ? Math.min(n, 4) : 3;
  const cw = scene.type === 'flow' ? 345 : 460,
    ch = 154,
    gap = 38,
    rows = Math.ceil(n / columns);
  const width = columns * cw + (columns - 1) * gap,
    left = (1720 - width) / 2;
  return (
    <svg width="1720" height="590" viewBox="0 0 1720 590">
      <defs>
        <marker
          id={'arrow-' + scene.id}
          markerWidth="9"
          markerHeight="9"
          refX="8"
          refY="4"
          orient="auto"
        >
          <path d="M0,0 L8,4 L0,8" fill={color} />
        </marker>
      </defs>
      {Array.from({ length: n - 1 }, (_, i) => {
        if (scene.type === 'architecture') return null;
        const col = i % columns,
          row = Math.floor(i / columns);
        const x = left + col * (cw + gap) + cw,
          y = (rows === 1 ? 170 : 90) + row * (ch + 100) + ch / 2;
        if (col === columns - 1) return null;
        return (
          <path
            key={'edge' + i}
            d={`M ${x + 4},${y} L ${x + gap - 8},${y}`}
            stroke={color}
            strokeWidth="3"
            markerEnd={`url(#arrow-${scene.id})`}
            opacity={reveal(f, 20 + i * 10)}
          />
        );
      })}
      {labels.slice(0, n).map((label, i) => {
        const x = left + (i % columns) * (cw + gap),
          y = (rows === 1 ? 170 : 90) + Math.floor(i / columns) * (ch + 100);
        const active = Math.floor(Math.max(0, f - 24) / 65) % n === i;
        return (
          <g key={i} opacity={reveal(f, i * 8)}>
            <rect
              x={x}
              y={y}
              width={cw}
              height={ch}
              rx="18"
              fill={active ? color + '12' : '#fff'}
              stroke={active ? color : '#c4cee1'}
              strokeWidth={active ? 3 : 2}
            />
            <text x={x + 25} y={y + 41} fontSize="19" fill={color}>
              0{i + 1}
            </text>
            <foreignObject x={x + 25} y={y + 59} width={cw - 50} height="82">
              <div
                style={{
                  fontSize: 26,
                  fontWeight: 650,
                  lineHeight: 1.35,
                  color: '#1b2c49',
                  overflowWrap: 'anywhere',
                }}
              >
                {label}
              </div>
            </foreignObject>
          </g>
        );
      })}
    </svg>
  );
}

function DesignedDiagram({ scene, color }: { scene: Scene; color: string }) {
  const frame = useCurrentFrame();
  const graph = scene.diagram!;
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]));
  return (
    <svg width="1720" height="590" viewBox="0 0 1720 590">
      <defs>
        <marker
          id={'design-arrow-' + scene.id}
          markerWidth="8"
          markerHeight="8"
          refX="7"
          refY="4"
          orient="auto"
        >
          <path d="M0,0 L8,4 L0,8" fill={color} />
        </marker>
      </defs>
      {graph.edges.map((edge, i) => {
        const a = nodes.get(edge.source)!,
          b = nodes.get(edge.target)!;
        const dx = b.x - a.x,
          dy = b.y - a.y;
        const horizontal = Math.abs(dx) > Math.abs(dy);
        const x1 = a.x + 120 + (horizontal ? Math.sign(dx) * 120 : 0);
        const y1 = a.y + 50 + (horizontal ? 0 : Math.sign(dy) * 50);
        const x2 = b.x + 120 - (horizontal ? Math.sign(dx) * 120 : 0);
        const y2 = b.y + 50 - (horizontal ? 0 : Math.sign(dy) * 50);
        const shown = reveal(frame, edge.reveal * scene.frames);
        return (
          <g key={i} opacity={shown}>
            <path
              d={`M${x1},${y1} L${x2},${y2}`}
              pathLength={1}
              strokeDasharray="1"
              strokeDashoffset={1 - shown}
              stroke={color}
              strokeWidth="3"
              fill="none"
              markerEnd={`url(#design-arrow-${scene.id})`}
            />
            {edge.label && (
              <text
                x={(x1 + x2) / 2}
                y={(y1 + y2) / 2 - 12}
                textAnchor="middle"
                fill="#425674"
                fontSize="18"
              >
                {edge.label}
              </text>
            )}
          </g>
        );
      })}
      {graph.nodes.map((node) => {
        const shown = reveal(frame, node.reveal * scene.frames);
        const pulse =
          node.emphasis === 'pulse'
            ? 1 + 0.018 * Math.sin(Math.max(0, frame - node.reveal * scene.frames) / 9)
            : 1;
        return (
          <g
            key={node.id}
            opacity={shown}
            transform={`translate(${node.x + 120} ${node.y + 50 + (1 - shown) * 12}) scale(${pulse}) translate(-120 -50)`}
          >
            <rect width="240" height="100" rx="16" fill="#ffffff" stroke={color} strokeWidth="2" />
            <rect x="0" y="20" width="5" height="60" rx="2" fill={color} />
            <text
              x="120"
              y={node.detail ? 40 : 58}
              textAnchor="middle"
              fill="#172d4b"
              fontSize={node.label.length > 14 ? 18 : 24}
              fontWeight="700"
            >
              {node.label}
            </text>
            {node.detail && (
              <text x="120" y="71" textAnchor="middle" fill="#5a6d86" fontSize="16">
                {node.detail}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function Content({ scene, color }: { scene: Scene; color: string }) {
  const f = useCurrentFrame();
  if (scene.media_src)
    return (
      <div
        style={{
          width: 1720,
          height: 640,
          borderRadius: 20,
          overflow: 'hidden',
          border: '1px solid #bbc9df',
          background: '#fff',
        }}
      >
        {scene.media_kind === 'video' ? (
          <OffthreadVideo
            muted
            src={source(scene.media_src)}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <Img
            src={source(scene.media_src)}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        )}
      </div>
    );
  if (scene.diagram) return <DesignedDiagram scene={scene} color={color} />;
  if (scene.type === 'flow' || scene.type === 'architecture')
    return <Graph scene={scene} color={color} />;
  if (scene.type === 'code' || scene.type === 'terminal')
    return (
      <div
        style={{
          width: 1720,
          height: 630,
          borderRadius: 22,
          background: '#142238',
          boxShadow: '0 24px 60px #132c4d20',
          overflow: 'hidden',
          color: '#e2edf9',
        }}
      >
        <div
          style={{
            height: 48,
            background: '#203049',
            padding: '12px 24px',
            display: 'flex',
            gap: 9,
            alignItems: 'center',
          }}
        >
          {['#f28c86', '#e7c172', '#8cc6b5'].map((c) => (
            <i key={c} style={{ width: 10, height: 10, borderRadius: 9, background: c }} />
          ))}
          <span style={{ fontSize: 16, marginLeft: 18, color: '#b8c9e2' }}>
            {scene.subtitle || 'SOURCE / OBSERVED OUTPUT'}
          </span>
        </div>
        <pre
          style={{
            fontFamily: 'ExplainerNoto, ui-monospace, monospace',
            fontSize: 22,
            lineHeight: 1.55,
            padding: '18px 32px',
            margin: 0,
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
            maxHeight: 555,
            overflow: 'hidden',
          }}
        >
          {scene.code || scene.narration}
        </pre>
      </div>
    );
  if (scene.type === 'title' || scene.type === 'summary')
    return (
      <div style={{ width: 1720, paddingTop: 55 }}>
        <div style={{ color, fontSize: 20, letterSpacing: 5, marginBottom: 28 }}>
          IDEAS INTO UNDERSTANDING
        </div>
        <div
          style={{
            fontSize: scene.title.length > 35 ? 58 : 76,
            fontWeight: 750,
            maxWidth: 1520,
            lineHeight: 1.4,
            letterSpacing: -2,
          }}
        >
          {scene.title}
        </div>
        <div style={{ width: 100, height: 5, background: color, margin: '35px 0' }} />
        <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
          {scene.bullets.slice(0, 4).map((b, i) => (
            <div
              key={i}
              style={{
                opacity: reveal(f, 15 + i * 8),
                background: '#ffffffc0',
                padding: '20px 26px',
                border: '1px solid #d2dceb',
                borderRadius: 14,
                fontSize: 24,
                maxWidth: 740,
                lineHeight: 1.5,
              }}
            >
              {b}
            </div>
          ))}
        </div>
      </div>
    );
  return (
    <div
      style={{
        width: 1720,
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 24,
        paddingTop: 20,
      }}
    >
      {(scene.bullets.length ? scene.bullets : [scene.narration]).slice(0, 6).map((b, i) => (
        <div
          key={i}
          style={{
            minHeight: 165,
            opacity: reveal(f, i * 8),
            transform: `translateY(${(1 - reveal(f, i * 8)) * 20}px)`,
            background: '#fff',
            border: '1px solid #cad5e6',
            borderRadius: 19,
            padding: '26px 30px',
            boxShadow: '0 10px 24px #233a5a05',
          }}
        >
          <div style={{ color, fontSize: 20, fontWeight: 700, marginBottom: 18 }}>0{i + 1}</div>
          <div
            style={{
              fontSize: b.length > 90 ? 24 : 29,
              lineHeight: 1.55,
              overflowWrap: 'anywhere',
            }}
          >
            {b}
          </div>
        </div>
      ))}
    </div>
  );
}

function SceneView({
  scene,
  index,
  total,
  accent,
  language,
  props,
}: {
  scene: Scene;
  index: number;
  total: number;
  accent: string;
  language: string;
  props: VideoProps;
}) {
  const f = useCurrentFrame(),
    { fps } = useVideoConfig();
  const progress = Math.min(1, f / Math.max(scene.frames - 1, 1));
  const objectScene = Boolean(scene.visual_scene || scene.semantic_scene);
  const theme = useTheme();
  const bookend =
    (props.presentation_profile || 'creator') === 'creator' &&
    (scene.role === 'opening' || scene.role === 'closing');
  const opacity = scene.type === 'title' || scene.role === 'opening' ? 1 : reveal(f);
  const cue = scene.cues.find((c) => f / fps >= c.start && f / fps < c.end);
  const text = cue?.text || (!scene.cues.length ? scene.narration.slice(0, 65) : '');
  const labels = {
    static: language === 'zh-CN' ? '源码静态观察' : 'SOURCE EVIDENCE',
    runtime: language === 'zh-CN' ? '本次运行观察' : 'OBSERVED RUN',
    concept: language === 'zh-CN' ? '概念讲解' : 'CONCEPT',
    user_provided: language === 'zh-CN' ? '用户提供内容' : 'USER BRIEF',
  };
  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg,#f8faff,#edf2f8)',
        color: '#172a47',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: 1000,
          height: 1000,
          right: -510,
          top: -570,
          border: `1px solid ${accent}20`,
          borderRadius: '50%',
        }}
      />
      {objectScene &&
        (scene.semantic_scene ? (
          <SceneRenderer
            scene={scene}
            assets={props.generated_assets}
            designPack={props.design_pack}
          />
        ) : (
          <ObjectScene scene={scene} />
        ))}
      {(props.presentation_profile || 'creator') !== 'creator' && (
        <div
          style={{
            position: 'absolute',
            top: 48,
            left: 100,
            right: 100,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: 18, letterSpacing: 4, color: accent }}>
            EXPLAINER STUDIO / {String(index + 1).padStart(2, '0')}
          </span>
          <Badge text={labels[scene.verification]} color={accent} />
        </div>
      )}
      {!objectScene && !bookend && scene.type !== 'title' && scene.type !== 'summary' && (
        <div
          style={{
            position: 'absolute',
            top: 105,
            left: 100,
            right: 100,
            fontSize: 48,
            fontWeight: 720,
            opacity,
            lineHeight: 1.35,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {scene.title}
        </div>
      )}
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: scene.type === 'title' || scene.type === 'summary' ? 200 : 220,
          opacity,
        }}
      >
        {!objectScene && !bookend && <Content scene={scene} color={accent} />}
      </div>
      {!objectScene &&
        (props.presentation_profile || 'creator') === 'creator' &&
        (scene.role === 'opening' || scene.role === 'closing') && (
          <Bookend scene={scene} props={props} />
        )}
      <ViewerDisclosures scene={scene} fps={fps} />
      {text && (
        <div
          style={{ position: 'absolute', bottom: 72, left: 140, right: 140, textAlign: 'center' }}
        >
          <span
            style={{
              display: 'inline-block',
              fontSize: 28,
              lineHeight: 1.55,
              maxWidth: 1560,
              padding: '10px 24px',
              color: theme.ink,
              background: theme.panel + 'd9',
              border: '1px solid ' + theme.border,
              borderRadius: 12,
            }}
          >
            {text}
          </span>
        </div>
      )}
      <div
        style={{ position: 'absolute', left: 100, right: 100, bottom: 28, display: 'flex', gap: 7 }}
      >
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            style={{
              height: 3,
              flex: 1,
              background:
                i < index
                  ? accent
                  : i === index
                    ? `linear-gradient(to right,${accent} ${progress * 100}%,#d6e0ed ${progress * 100}%)`
                    : '#d6e0ed',
            }}
          />
        ))}
      </div>
      {scene.audio_src && <Audio src={source(scene.audio_src)} />}
      <ObjectSceneSounds scene={scene} fps={fps} preview={props.preview} />
    </AbsoluteFill>
  );
}

export function Video(props: VideoProps) {
  const [handle] = useState(() => delayRender('font'));
  useEffect(() => {
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        continueRender(handle);
      }
    };
    const font = new FontFace('ExplainerNoto', `url(${props.fontSrc || staticFile('noto.otf')})`);
    font
      .load()
      .then((v) => (document.fonts as unknown as { add(font: FontFace): void }).add(v))
      .then(finish)
      .catch((error) => cancelRender(error));
    return finish;
  }, [handle, props.fontSrc]);
  return (
    <ThemeProvider pack={props.design_pack}>
      <AbsoluteFill
        style={{
          fontFamily: 'ExplainerNoto, system-ui, sans-serif',
          width: 1920,
          height: 1080,
          transform: `scale(${(props.width || 1920) / 1920})`,
          transformOrigin: 'top left',
        }}
      >
        {props.scenes.map((scene, index) => (
          <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
            <SceneView
              scene={scene}
              index={index}
              total={props.scenes.length}
              accent={colors[props.accent]}
              language={props.language}
              props={props}
            />
          </Sequence>
        ))}
      </AbsoluteFill>
    </ThemeProvider>
  );
}
