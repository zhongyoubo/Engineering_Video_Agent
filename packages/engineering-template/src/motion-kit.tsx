import { PublicationCard } from './presentation';
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import type { Scene } from './contracts';

// Trusted, frame-driven building blocks. Source labels are supplied by the plan,
// never inferred as runtime facts. Coordinates use a 1920x1080 logical canvas.
export const designPacks = {
  editorial_warm: {
    background: '#f4efe5',
    ink: '#273b38',
    accent: '#a63d49',
    panel: '#fffdf7',
    muted: '#7a8580',
  },
  workspace_tech: {
    background: '#eef4fa',
    ink: '#17354b',
    accent: '#087f83',
    panel: '#ffffff',
    muted: '#718698',
  },
};
type Pack = keyof typeof designPacks;
type Action = 'reveal' | 'highlight' | 'progress';
const clamp = (f: number, start: number, end: number) =>
  interpolate(f, [start, Math.max(start + 1, end)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

export function motionProgress(
  scene: Scene,
  target: string,
  frame: number,
  action: Action = 'progress',
  fallback = 1,
) {
  const event = scene.compiled_events?.find((e) => e.target === target && e.action === action);
  return event ? clamp(frame, event.start_frame, event.end_frame) : fallback;
}

export function MotionScene({
  scene,
  designPack = 'workspace_tech',
}: {
  scene: Scene;
  designPack?: Pack;
}) {
  const frame = useCurrentFrame();
  const pack = designPacks[designPack];
  const spec = scene.motion;
  if (!spec) throw new Error('MotionScene requires a validated scene.motion specification');
  const elements = spec.elements;
  const phase = clamp(frame, 0, Math.max(30, scene.frames - 20));
  const progress = (i: number) => motionProgress(scene, elements[i]?.id, frame, 'progress', phase);
  const opacity = (i: number) =>
    motionProgress(scene, elements[i]?.id, frame, 'reveal', clamp(frame, i * 8, i * 8 + 18));
  const highlight = (i: number) => motionProgress(scene, elements[i]?.id, frame, 'highlight', 0);
  const card = (i: number, x: number, y: number, width = 350, height = 170) => (
    <g
      key={elements[i].id}
      opacity={opacity(i)}
      transform={`translate(${x},${y + (1 - opacity(i)) * 22})`}
    >
      <rect
        width={width}
        height={height}
        rx="16"
        fill={pack.panel}
        stroke={highlight(i) > 0.5 ? pack.accent : '#ccd6d4'}
        strokeWidth={highlight(i) > 0.5 ? 4 : 2}
      />
      <text x="25" y="45" fontSize="20" fill={pack.accent}>
        {String(i + 1).padStart(2, '0')}
      </text>
      <foreignObject x="25" y="65" width={width - 50} height={height - 75}>
        <div
          style={{
            fontSize: height < 150 ? 18 : 26,
            lineHeight: height < 150 ? 1.35 : 1.4,
            color: pack.ink,
            overflowWrap: 'anywhere',
          }}
        >
          {elements[i].label}
        </div>
      </foreignObject>
    </g>
  );
  const content = () => {
    if (spec.pattern === 'code_scan')
      return (
        <>
          <rect x="0" y="10" width="1040" height="570" rx="20" fill="#102e34" />
          {scene.code
            .split('\n')
            .slice(0, 14)
            .map((line, i) => (
              <text
                key={i}
                x="30"
                y={55 + i * 35}
                fontFamily="monospace"
                fontSize="23"
                fill="#d9ebe6"
                opacity={0.65 + 0.35 * progress(0)}
              >
                {line.slice(0, 68)}
              </text>
            ))}
          <rect x="0" y={30 + progress(0) * 480} width="1040" height="3" fill={pack.accent} />
          {elements.slice(0, 4).map((_, i) => card(i, 1100, 15 + i * 145, 600, 125))}
        </>
      );
    if (spec.pattern === 'compare')
      return elements.slice(0, 3).map((_, i) => {
        const width = elements.length === 2 ? 790 : 520;
        return card(i, i * (width + 40), 120, width, 320);
      });
    if (spec.pattern === 'graph')
      return (
        <>
          {elements.slice(1).map((e, i) => {
            const angle = (i / Math.max(1, elements.length - 1)) * Math.PI * 2;
            const x = 860 + Math.cos(angle) * 600,
              y = 295 + Math.sin(angle) * 210;
            return (
              <g key={e.id} opacity={opacity(i + 1)}>
                <path
                  d={`M860 295 Q860 ${y} ${x} ${y}`}
                  fill="none"
                  stroke={pack.accent}
                  strokeWidth="3"
                  pathLength="1"
                  strokeDasharray="1"
                  strokeDashoffset={1 - progress(i + 1)}
                />
                <circle
                  cx={x}
                  cy={y}
                  r="65"
                  fill={pack.panel}
                  stroke={pack.accent}
                  strokeWidth="2"
                />
                <foreignObject x={x - 125} y={y - 25} width="250" height="80">
                  <div style={{ textAlign: 'center', fontSize: 24, color: pack.ink }}>
                    {e.label}
                  </div>
                </foreignObject>
              </g>
            );
          })}
          <circle cx="860" cy="295" r="85" fill={pack.ink} />
          <foreignObject x="790" y="245" width="140" height="110">
            <div
              style={{
                textAlign: 'center',
                fontSize: 22,
                lineHeight: 1.25,
                color: 'white',
                overflowWrap: 'anywhere',
              }}
            >
              {elements[0].label}
            </div>
          </foreignObject>
        </>
      );
    if (spec.pattern === 'capacity')
      return (
        <>
          <rect
            x="430"
            y="20"
            width="840"
            height="550"
            rx="22"
            fill={pack.panel}
            stroke={pack.muted}
            strokeWidth="3"
          />
          {elements.map((e, i) => (
            <g key={e.id} opacity={opacity(i)}>
              <rect
                x="460"
                y={500 - i * 62}
                width={760 * progress(i)}
                height="45"
                rx="8"
                fill={i === elements.length - 1 ? pack.accent : '#acc7c7'}
              />
              <text x="480" y={530 - i * 62} fontSize="23" fill={pack.ink}>
                {e.label}
              </text>
            </g>
          ))}
        </>
      );
    if (spec.pattern === 'depth')
      return (
        <>
          <rect y="180" width="1720" height="410" fill="#d8c4a4" />
          <path d="M0 180 H1720" stroke="#96816b" strokeWidth="3" />
          {Array.from({ length: Math.min(8, Math.floor(progress(0) * 9)) }, (_, i) => (
            <g key={i}>
              <path d={`M${70 + i * 90} 180 q25 65 50 0`} fill="#a38f75" />
              <path
                d={`M${95 + i * 90} 180 v-35 l20 8 -20 8`}
                fill={pack.muted}
                stroke={pack.muted}
              />
            </g>
          ))}
          <rect
            x="1160"
            y="180"
            width="64"
            height={60 + progress(Math.min(1, elements.length - 1)) * 320}
            fill={pack.ink}
          />
          <path d="M1140 180 l52 -75 52 75" fill="none" stroke={pack.ink} strokeWidth="3" />
          {elements.slice(0, 2).map((e, i) => (
            <foreignObject key={e.id} x={i ? 1050 : 90} y="45" width="530" height="100">
              <div
                style={{
                  fontSize: 28,
                  lineHeight: 1.35,
                  color: pack.ink,
                  overflowWrap: 'anywhere',
                }}
              >
                {e.label}
              </div>
            </foreignObject>
          ))}
        </>
      );
    if (spec.pattern === 'queue')
      return (
        <>
          <rect x="1350" y="80" width="300" height="420" rx="20" fill={pack.ink} />
          <foreignObject x="1375" y="110" width="250" height="120">
            <div
              style={{
                fontSize: 26,
                lineHeight: 1.3,
                color: 'white',
                textAlign: 'center',
                overflowWrap: 'anywhere',
              }}
            >
              {elements[elements.length - 1].label}
            </div>
          </foreignObject>
          <rect x="1280" y="140" width="14" height="300" fill={pack.accent} />
          {Array.from({ length: 28 }, (_, i) => {
            const y = 65 + i * 17,
              t = (frame * 0.003 + i / 28) % 1;
            const x = (1 - t) * (1 - t) * 80 + 2 * (1 - t) * t * 800 + t * t * 1270;
            const cy = (1 - t) * (1 - t) * y + 2 * (1 - t) * t * y + t * t * 290;
            return (
              <g key={i} opacity={opacity(0)}>
                <path
                  d={`M80 ${y} Q800 ${y} 1270 290`}
                  stroke={pack.muted}
                  strokeWidth="1"
                  fill="none"
                  opacity=".25"
                />
                <circle cx={x} cy={cy} r="5" fill={pack.accent} />
              </g>
            );
          })}
          {Array.from(
            { length: Math.floor(progress(Math.min(1, elements.length - 1)) * 20) },
            (_, i) => (
              <rect
                key={i}
                x={1170 - (i % 5) * 32}
                y={220 + Math.floor(i / 5) * 32}
                width="22"
                height="22"
                rx="4"
                fill={pack.accent}
              />
            ),
          )}
          <text x="80" y="570" fill={pack.ink} fontSize="28">
            {elements[0].label}
          </text>
          {elements.length === 3 && (
            <text x="1050" y="420" fill={pack.accent} fontSize="26">
              {elements[1].label}
            </text>
          )}
        </>
      );
    if (spec.layout === 'fan')
      return elements.map((element, i) => {
        const count = elements.length;
        const width = Math.min(290, 1500 / count);
        const step = count > 1 ? Math.min(280, 1450 / (count - 1)) : 0;
        const angle = (i - (count - 1) / 2) * 5;
        const x = 860 + (i - (count - 1) / 2) * step - width / 2;
        const y = 115 + Math.abs(angle) * 3;
        return (
          <g key={element.id} transform={`rotate(${angle * 0.55},${x + width / 2},${y + 150})`}>
            {card(i, x, y, width, 340)}
          </g>
        );
      });
    return elements.map((_, i) => {
      const count = Math.min(elements.length, 4),
        row = Math.floor(i / count),
        col = i % count;
      return card(i, col * 425, 70 + row * 240, 390, 210);
    });
  };
  return (
    <AbsoluteFill style={{ background: pack.background, color: pack.ink }}>
      <div
        style={{
          position: 'absolute',
          top: 65,
          left: 100,
          fontSize: 18,
          letterSpacing: 3,
          color: pack.muted,
        }}
      >
        {spec.chapter}
      </div>
      <div
        style={{
          position: 'absolute',
          top: 115,
          left: 100,
          right: 100,
          fontSize: scene.title.length > 64 ? 32 : scene.title.length > 32 ? 40 : 48,
          fontWeight: 700,
          lineHeight: 1.3,
        }}
      >
        {scene.title}
      </div>
      <svg
        style={{ position: 'absolute', left: 100, top: 270 }}
        width="1720"
        height="590"
        viewBox="0 0 1720 590"
      >
        {content()}
      </svg>
    </AbsoluteFill>
  );
}

export type BookendProps = {
  designPack?: Pack;
  projectName?: string;
  headline?: string;
  subtitle?: string;
  repository?: string;
};

/** Topic-driven bookends. No tool branding or production credits by default. */
export function CoverScene({
  designPack = 'editorial_warm',
  projectName = '',
  headline = '',
  subtitle = '',
}: BookendProps) {
  return (
    <PublicationCard
      headline={headline || projectName}
      subtitle={subtitle}
      warm={designPack === 'editorial_warm'}
    />
  );
}

export function EndScene({
  projectName = '',
  headline = '',
  subtitle = '',
  repository = '',
}: BookendProps) {
  return (
    <PublicationCard headline={headline || projectName} subtitle={subtitle || repository} closing />
  );
}
