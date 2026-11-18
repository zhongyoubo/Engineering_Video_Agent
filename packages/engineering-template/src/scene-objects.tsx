/** Platform-owned, data-only object stage. No uploaded code, URLs or random clocks. */
import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from 'remotion';
import type { Scene, VisualScene, CompiledObjectEvent } from './contracts';

type Actor = VisualScene['objects'][number];
type Link = VisualScene['connections'][number];
type Point = { x: number; y: number };
const clamp = (x: number) => Math.max(0, Math.min(1, x));
const amount = (frame: number, e: CompiledObjectEvent) =>
  clamp((frame - e.start_frame) / Math.max(1, e.end_frame - e.start_frame));
const colors = { video: '#3279ed', audio: '#9a4fd1', control: '#d58a17', data: '#0a9991' };
function endpoint(o: Actor, id: string): Point {
  const p = o.ports.find((p) => p.id === id)!;
  return {
    x: o.x + (p.side === 'left' ? 0 : p.side === 'right' ? o.width : p.position * o.width),
    y: o.y + (p.side === 'top' ? 0 : p.side === 'bottom' ? o.height : p.position * o.height),
  };
}
function curve(a: Point, b: Point) {
  const dx = Math.max(70, Math.abs(b.x - a.x) * 0.38);
  const sign = b.x >= a.x ? 1 : -1;
  const c = { x: a.x + dx * sign, y: a.y },
    d = { x: b.x - dx * sign, y: b.y };
  return {
    path: `M${a.x},${a.y} C${c.x},${c.y} ${d.x},${d.y} ${b.x},${b.y}`,
    point: (t: number) => ({
      x: (1 - t) ** 3 * a.x + 3 * (1 - t) ** 2 * t * c.x + 3 * (1 - t) * t * t * d.x + t ** 3 * b.x,
      y: (1 - t) ** 3 * a.y + 3 * (1 - t) ** 2 * t * c.y + 3 * (1 - t) * t * t * d.y + t ** 3 * b.y,
    }),
  };
}
function Picture({
  object,
  frame,
  playing,
  power,
}: {
  object: Actor;
  frame: number;
  playing: boolean;
  power: number;
}) {
  const f = playing ? frame : 0;
  const movement = object.playback === 'stepped' ? Math.floor(f / 9) * 9 : f;
  const x = 8 + ((movement * 0.65) % 78);
  return (
    <g opacity={power}>
      <rect width="100" height="100" fill={object.hdr ? '#298ade' : '#6b9ec3'} />
      <circle cx="76" cy="20" r={object.hdr ? 10 : 8} fill={object.hdr ? '#ffe7a8' : '#c7d0ca'} />
      {object.screen === 'game' ? (
        <>
          <path d="M0,45 L100,45 L100,100 L0,100Z" fill="#326b47" />
          <path d="M41,45 L61,45 L95,100 L5,100Z" fill="#394759" />
          {[0, 1, 2, 3].map((i) => (
            <rect
              key={i}
              x="49"
              y={46 + ((i * 18 + movement * 0.7) % 57)}
              width="3"
              height="10"
              fill="#e8dcb6"
            />
          ))}
          <g transform={`translate(${x * 0.65},72)`}>
            <rect width="25" height="12" rx="4" fill="#f39f48" />
            <rect x="5" y="-5" width="14" height="7" rx="2" fill="#dbeafa" />
            <circle cx="5" cy="12" r="3" fill="#172a38" />
            <circle cx="20" cy="12" r="3" fill="#172a38" />
          </g>
        </>
      ) : (
        <>
          <path
            d="M0,67 L24,28 L55,70 L81,39 L100,64 L100,100 L0,100Z"
            fill={object.hdr ? '#295f64' : '#5c7f84'}
          />
          <path
            d="M0,76 Q50,68 100,76 L100,100 L0,100Z"
            fill={object.hdr ? '#146e9f' : '#59879b'}
          />
          {[0, 1, 2].map((i) => (
            <path
              key={i}
              d={`M${-20 + ((movement * 0.2 + i * 30) % 130)},${83 + i * 5} h24`}
              stroke="#b6e8ec"
              strokeWidth=".8"
            />
          ))}
          <g transform={`translate(${x},78)`}>
            <path d="M-9,0 h18 l-4,4 h-10Z" fill="#f9c76e" />
            <path d="M0,0 v-16 l-10,14Z" fill="#f4f4e7" />
          </g>
        </>
      )}
      {object.screen === 'stream' && (
        <>
          <rect x="5" y="6" width="31" height="8" rx="2" fill="#ffffffcc" />
          <text x="20" y="12" textAnchor="middle" fontSize="4" fill="#173e42">
            VIDEO
          </text>
        </>
      )}
      {object.screen === 'pixels' &&
        Array.from({ length: 12 }, (_, i) => (
          <g key={i}>
            <path d={`M${i * 9},0 v100 M0,${i * 9} h100`} stroke="#ffffffa0" strokeWidth=".7" />
          </g>
        ))}
      {object.screen === 'black' && <rect width="100" height="100" fill="#112a35" />}
      {!object.hdr && <rect width="100" height="100" fill="#ddd5c5" opacity=".12" />}
    </g>
  );
}
function ObjectShape({
  o,
  frame,
  events,
  renderScreen,
  objectLabel,
  transparentBackground = false,
}: {
  o: Actor;
  frame: number;
  events: CompiledObjectEvent[];
  renderScreen?: (object: Actor, frame: number, width: number, height: number) => React.ReactNode;
  objectLabel?: (object: Actor) => string;
  transparentBackground?: boolean;
}) {
  const own = events.filter((e) => e.target === o.id);
  const powerEvents = own
    .filter((e) => (e.action === 'power_on' || e.action === 'power_off') && e.start_frame <= frame)
    .sort((a, b) => a.start_frame - b.start_frame);
  const last = powerEvents.at(-1);
  const power = last
    ? last.action === 'power_on'
      ? amount(frame, last)
      : 1 - amount(frame, last)
    : Number(o.powered);
  const play = own.find((e) => e.action === 'play' && e.start_frame <= frame);
  const sound = own.find(
    (e) => e.action === 'sound' && e.start_frame <= frame && frame < e.end_frame,
  );
  const press = own.find(
    (e) => e.action === 'press' && e.start_frame <= frame && frame < e.end_frame,
  );
  const highlight = own.find(
    (e) => e.action === 'highlight' && e.start_frame <= frame && frame < e.end_frame,
  );
  const volumeEvent = own
    .filter((e) => e.action === 'volume' && e.start_frame <= frame)
    .sort((a, b) => a.start_frame - b.start_frame)
    .at(-1);
  const volume = volumeEvent?.value ?? 0.65;
  const reveal = own.find((e) => e.action === 'reveal');
  const opacity = reveal ? amount(frame, reveal) : 1;
  const w = o.width,
    h = o.height;
  const display = (x: number, y: number, width: number, height: number) => {
    const content = renderScreen?.(o, frame, width, height);
    return (
      <svg
        x={x}
        y={y}
        width={width}
        height={height}
        viewBox={content ? `0 0 ${width} ${height}` : '0 0 100 100'}
        preserveAspectRatio="none"
      >
        {content ? (
          <foreignObject data-device-surface="screen" width={width} height={height}>
            {content}
          </foreignObject>
        ) : (
          <>
            <rect width="100" height="100" fill="#112331" />
            <Picture
              object={o}
              frame={Math.max(0, frame - (play?.start_frame || 0))}
              power={power}
              playing={Boolean(play)}
            />
          </>
        )}
      </svg>
    );
  };
  const waves = sound
    ? [0, 1, 2].map((i) => {
        const progress = ((frame - sound.start_frame) / 32 + i / 3) % 1;
        return (
          <g key={i} opacity={(1 - progress) * 0.65 * power}>
            <path
              d={`M${w + 16 + progress * 75},${h * 0.2 - progress * 20} Q${w + 46 + progress * 95},${h * 0.5} ${w + 16 + progress * 75},${h * 0.8 + progress * 20}`}
              fill="none"
              stroke={colors.audio}
              strokeWidth={3 + volume * 3}
            />
            <path
              d={`M${-16 - progress * 75},${h * 0.2 - progress * 20} Q${-46 - progress * 95},${h * 0.5} ${-16 - progress * 75},${h * 0.8 + progress * 20}`}
              fill="none"
              stroke={colors.audio}
              strokeWidth={3 + volume * 3}
            />
          </g>
        );
      })
    : null;
  let body: React.ReactNode;
  if (o.kind === 'tv' || o.kind === 'monitor')
    body = (
      <>
        <rect x="-10" y="-10" width={w + 20} height={h * 0.82 + 20} rx="20" fill="#223d4b0b" />
        <rect width={w} height={h * 0.82} rx="15" fill={o.color} />
        {display(12, 12, w - 24, h * 0.82 - 30)}
        <circle cx={w * 0.92} cy={h * 0.82 - 8} r="3" fill={power > 0.5 ? '#64e1c1' : '#ed8b6a'} />
        {o.kind === 'tv' ? (
          <>
            <path
              d={`M${w * 0.2},${h * 0.82} l-22,${h * 0.13} M${w * 0.8},${h * 0.82} l22,${h * 0.13}`}
              stroke={o.color}
              strokeWidth="12"
              strokeLinecap="round"
            />
          </>
        ) : (
          <>
            <rect x={w * 0.44} y={h * 0.82} width={w * 0.12} height={h * 0.12} fill={o.color} />
            <rect
              x={w * 0.27}
              y={h * 0.93}
              width={w * 0.46}
              height={h * 0.035}
              rx="8"
              fill={o.color}
            />
          </>
        )}
      </>
    );
  else if (o.kind === 'laptop')
    body = (
      <>
        <rect width={w} height={h * 0.76} rx="15" fill={o.color} />
        {display(12, 12, w - 24, h * 0.76 - 24)}
        <path
          d={`M0,${h * 0.76} L${w},${h * 0.76} L${w + 15},${h * 0.95} L-15,${h * 0.95}Z`}
          fill="#9dabb4"
        />
        <rect x={w * 0.37} y={h * 0.81} width={w * 0.26} height={h * 0.08} rx="4" fill="#657884" />
      </>
    );
  else if (o.kind === 'phone')
    body = (
      <>
        <rect width={w} height={h} rx="25" fill={o.color} />
        {display(8, 14, w - 16, h - 28)}
        <rect x={w * 0.3} y="6" width={w * 0.4} height="7" rx="3" fill="#071d2a" />
      </>
    );
  else if (o.kind === 'console')
    body = (
      <>
        <path
          d={`M${w * 0.25},0 Q${w * 0.05},${h * 0.3} ${w * 0.2},${h * 0.8} L${w * 0.74},${h * 0.8} Q${w * 0.95},${h * 0.3} ${w * 0.77},0Z`}
          fill="#e8edf1"
          stroke="#8596a4"
          strokeWidth="3"
        />
        <path
          d={`M${w * 0.48},3 Q${w * 0.4},${h * 0.3} ${w * 0.49},${h * 0.78}`}
          stroke="#2778e1"
          strokeWidth="10"
          fill="none"
        />
        <g transform={`translate(0,${h * 0.72})`}>
          <path
            d={`M${w * 0.2},0 Q0,${h * 0.02} 0,${h * 0.19} Q${w * 0.06},${h * 0.27} ${w * 0.3},${h * 0.14} L${w * 0.7},${h * 0.14} Q${w * 0.94},${h * 0.27} ${w},${h * 0.19} Q${w},0 ${w * 0.8},0Z`}
            fill={o.color}
          />
          <path
            d={`M${w * 0.2},${h * 0.06} v${h * 0.06} M${w * 0.16},${h * 0.09} h${w * 0.08}`}
            stroke="#dee8ed"
            strokeWidth="5"
          />
          <circle cx={w * 0.8} cy={h * 0.07} r="5" fill="#f7c576" />
        </g>
      </>
    );
  else if (o.kind === 'player')
    body = (
      <>
        <rect y={h * 0.12} width={w} height={h * 0.65} rx="18" fill={o.color} />
        <rect x={w * 0.12} y={h * 0.35} width={w * 0.52} height="8" rx="4" fill="#536c7a" />
        <circle cx={w * 0.88} cy={h * 0.44} r="7" fill={power > 0.5 ? '#64e1c1' : '#e58673'} />
        <rect x={w * 0.1} y={h * 0.77} width={w * 0.14} height="8" fill="#78909c" />
        <rect x={w * 0.76} y={h * 0.77} width={w * 0.14} height="8" fill="#78909c" />
      </>
    );
  else if (o.kind === 'soundbar')
    body = (
      <>
        <rect width={w} height={h} rx={h / 2} fill={o.color} />
        {Array.from({ length: Math.max(8, Math.floor(w / 18)) }, (_, i) => (
          <path
            key={i}
            d={`M${16 + i * 17},${h * 0.22} v${h * 0.56}`}
            stroke="#5a7480"
            strokeWidth="2"
          />
        ))}
        <circle cx={w * 0.87} cy={h * 0.5} r="4" fill={power > 0.5 ? '#73dfc2' : '#e3887a'} />
        {waves}
      </>
    );
  else if (o.kind === 'speaker')
    body = (
      <>
        <rect width={w} height={h} rx="14" fill={o.color} />
        <circle cx={w / 2} cy={h * 0.25} r={Math.min(w * 0.27, h * 0.18)} fill="#637c89" />
        <circle cx={w / 2} cy={h * 0.66} r={Math.min(w * 0.38, h * 0.25)} fill="#4f6b7b" />
        <circle cx={w / 2} cy={h * 0.66} r={Math.min(w * 0.23, h * 0.15)} fill="#1a3442" />
        {waves}
      </>
    );
  else if (o.kind === 'remote')
    body = (
      <>
        <rect width={w} height={h} rx={Math.min(28, w * 0.3)} fill={o.color} />
        <circle cx={w / 2} cy={h * 0.16} r={w * 0.14} fill={press ? '#f5c264' : '#df816f'} />
        <circle cx={w / 2} cy={h * 0.4} r={w * 0.3} fill="#6d8492" />
        <circle cx={w / 2} cy={h * 0.4} r={w * 0.14} fill="#2a4657" />
        {[0, 1, 2].map((i) => (
          <g key={i}>
            <rect
              x={w * 0.2}
              y={h * (0.62 + i * 0.09)}
              width={w * 0.23}
              height={h * 0.045}
              rx="3"
              fill="#718897"
            />
            <rect
              x={w * 0.57}
              y={h * (0.62 + i * 0.09)}
              width={w * 0.23}
              height={h * 0.045}
              rx="3"
              fill="#718897"
            />
          </g>
        ))}
        {press && (
          <circle
            cx={w / 2}
            cy={h * 0.16}
            r={w * (0.2 + 0.6 * amount(frame, press))}
            stroke={colors.control}
            fill="none"
            strokeWidth="5"
            opacity={1 - amount(frame, press)}
          />
        )}
      </>
    );
  else if (o.kind === 'server')
    body = (
      <>
        <rect width={w} height={h} rx="12" fill={o.color} />
        {[0, 1, 2].map((i) => (
          <g key={i}>
            <rect
              x="12"
              y={12 + (i * (h - 20)) / 3}
              width={w - 24}
              height={(h - 40) / 3}
              rx="8"
              fill="#3d5869"
            />
            <path
              d={`M25,${35 + (i * (h - 20)) / 3} h${w * 0.5}`}
              stroke="#a2b4bd"
              strokeWidth="4"
            />
            <circle
              cx={w - 30}
              cy={35 + (i * (h - 20)) / 3}
              r="5"
              fill={power > 0.5 ? '#6adabb' : '#a6a5a2'}
            />
          </g>
        ))}
      </>
    );
  else
    body = (
      <>
        <path
          d={`M${w * 0.15},${h * 0.3} v-${h * 0.28} M${w * 0.85},${h * 0.3} v-${h * 0.28}`}
          stroke={o.color}
          strokeWidth="8"
          strokeLinecap="round"
        />
        <rect y={h * 0.3} width={w} height={h * 0.55} rx="18" fill={o.color} />
        {[0, 1, 2, 3].map((i) => (
          <circle
            key={i}
            cx={w * (0.15 + i * 0.18)}
            cy={h * 0.58}
            r="4"
            fill={power > 0.5 ? '#62dabb' : '#8a8f91'}
          />
        ))}
      </>
    );
  return (
    <g
      data-object-kind={o.kind}
      data-object-id={o.id}
      opacity={opacity}
      transform={`translate(${o.x},${o.y + (1 - opacity) * 12})`}
    >
      <ellipse cx={w / 2} cy={h + 6} rx={w * 0.55} ry="10" fill="#183f4210" />
      {highlight && (
        <rect
          x="-12"
          y="-12"
          width={w + 24}
          height={h + 24}
          rx="20"
          stroke="#d99b36"
          strokeWidth="4"
          fill="none"
        />
      )}
      {body}
      {!['soundbar', 'speaker'].includes(o.kind) && waves}
      {o.ports.map((p) => {
        const a = endpoint({ ...o, x: 0, y: 0 }, p.id);
        return (
          <g key={p.id} transform={`translate(${a.x},${a.y})`}>
            {p.kind === 'wireless' ? (
              <circle r="4" fill={colors.control} />
            ) : p.kind === 'network' ? (
              <>
                <rect
                  x="-10"
                  y="-8"
                  width="20"
                  height="16"
                  fill="#18394b"
                  stroke="#a7bac3"
                  strokeWidth="2"
                />
                <path d="M-7,-2 h14" stroke="#ddc17c" strokeWidth="3" />
              </>
            ) : (
              <>
                <path
                  d="M-11,-6 h22 l-3,12 h-16Z"
                  fill="#0c2635"
                  stroke="#a2b3bc"
                  strokeWidth="2"
                />
                <path d="M-6,-1 h12" stroke="#d2b57a" strokeWidth="2" />
              </>
            )}
            {p.label && (
              <text x="0" y="-14" fontSize="17" textAnchor="middle" fill="#526b7e">
                {p.label}
              </text>
            )}
          </g>
        );
      })}
      <foreignObject
        x={Math.max(-o.x, Math.min(w / 2 - 160, 1720 - o.x - 320))}
        y={h + 15}
        width="320"
        height="80"
      >
        <div
          style={{
            textAlign: 'center',
            color: '#294b56',
            fontSize: 25,
            lineHeight: 1.25,
            overflowWrap: 'anywhere',
          }}
        >
          {objectLabel?.(o) || o.label}
        </div>
      </foreignObject>
      {volumeEvent && (
        <g transform={`translate(${w / 2 - 55},${h * 0.45})`}>
          <rect width="110" height="48" rx="9" fill="#fffdf4ee" />
          <text x="55" y="32" fontSize="26" textAnchor="middle" fill="#173e42">
            VOL {Math.round(volume * 100)}
          </text>
        </g>
      )}
    </g>
  );
}
function Connection({
  link,
  objects,
  events,
  frame,
}: {
  link: Link;
  objects: Actor[];
  events: CompiledObjectEvent[];
  frame: number;
}) {
  const a = endpoint(objects.find((o) => o.id === link.source)!, link.source_port),
    b = endpoint(objects.find((o) => o.id === link.target)!, link.target_port),
    wire = curve(a, b);
  const own = events.filter((e) => e.target === link.id),
    connect = own.find((e) => e.action === 'connect');
  const connected = connect ? amount(frame, connect) : Number(link.connected);
  const active = own.filter(
    (e) =>
      e.action === 'signal' && frame >= e.start_frame && frame < e.end_frame && connected > 0.95,
  );
  const mid = wire.point(0.5);
  return (
    <g data-connection-id={link.id}>
      <path
        d={wire.path}
        fill="none"
        stroke="#294856"
        strokeWidth={link.kind === 'cable' ? 10 : 3}
        strokeDasharray={link.kind === 'wireless' ? '8 12' : undefined}
        opacity={link.kind === 'cable' ? 0.15 : connected * 0.5}
      />
      {link.kind === 'cable' && (
        <path
          d={wire.path}
          pathLength="1"
          strokeDasharray="1"
          strokeDashoffset={1 - connected}
          fill="none"
          stroke="#2b4e5d"
          strokeWidth="9"
          strokeLinecap="round"
          opacity={connected}
        />
      )}
      {link.kind === 'cable' &&
        [a, b].map((p, i) => (
          <g
            key={i}
            opacity={Math.max(0.25, connected)}
            transform={`translate(${p.x + (i === 1 ? (1 - connected) * 32 * (b.x >= a.x ? -1 : 1) : 0)},${p.y})`}
          >
            <rect x="-15" y="-8" width="30" height="16" rx="4" fill="#345567" />
            <path d="M-6,-7 h12 l-2,14 h-8Z" fill="#b8a174" />
          </g>
        ))}
      {connect && frame >= connect.start_frame && frame < connect.end_frame && (
        <circle
          cx={b.x}
          cy={b.y}
          r={22 + amount(frame, connect) * 20}
          stroke="#d7a247"
          strokeWidth="4"
          fill="none"
          opacity={1 - amount(frame, connect)}
        />
      )}
      {link.label && (
        <g transform={`translate(${mid.x},${mid.y + 35})`}>
          <rect
            x={-Math.max(65, link.label.length * 12)}
            y="-23"
            width={Math.max(130, link.label.length * 24)}
            height="34"
            rx="8"
            fill="#fffdf5ef"
          />
          <text textAnchor="middle" fontSize="23" fill="#526b79">
            {link.label}
          </text>
        </g>
      )}
      {active.map((e) =>
        Array.from({ length: 6 }, (_, i) => {
          const phase = ((frame - e.start_frame) / 75 + i / 6) % 1;
          const p = wire.point(e.reverse ? 1 - phase : phase);
          const color = colors[e.channel];
          return (
            <g key={e.id + '-' + i} transform={`translate(${p.x},${p.y})`}>
              {e.channel === 'video' ? (
                <>
                  <rect
                    x="-13"
                    y="-9"
                    width="26"
                    height="18"
                    rx="3"
                    fill={color}
                    stroke="#fff"
                    strokeWidth="1.5"
                  />
                  <path d="M-9,5 L-2,-3 L2,1 L7,-3 L11,5Z" fill="#d1ecff" />
                </>
              ) : e.channel === 'audio' ? (
                <path
                  d="M-13,0 l4,-8 l5,16 l5,-17 l5,16 l5,-7"
                  fill="none"
                  stroke={color}
                  strokeWidth="4"
                  strokeLinejoin="round"
                />
              ) : (
                <>
                  <circle r="10" fill={color} />
                  <circle r="15" fill="none" stroke={color} opacity=".3" />
                </>
              )}
            </g>
          );
        }),
      )}
    </g>
  );
}
export function ObjectScene({
  scene,
  frameOverride,
  titleOverride,
  renderScreen,
  objectLabel,
  transparentBackground = false,
}: {
  scene: Scene;
  frameOverride?: number;
  titleOverride?: string;
  renderScreen?: (object: Actor, frame: number, width: number, height: number) => React.ReactNode;
  objectLabel?: (object: Actor) => string;
  transparentBackground?: boolean;
}) {
  const current = useCurrentFrame(),
    frame = frameOverride ?? current,
    spec = scene.visual_scene;
  if (!spec) return null;
  const events = scene.compiled_object_events || [];
  return (
    <AbsoluteFill
      data-object-scene
      style={{
        background: transparentBackground
          ? 'transparent'
          : spec.setting === 'living_room'
            ? '#f5eee1'
            : '#edf4f7',
        color: '#173e42',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 100,
          right: 100,
          top: 70,
          fontSize: titleOverride ? 64 : 48,
          fontWeight: 750,
          lineHeight: 1.3,
        }}
      >
        {titleOverride || scene.title}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 175,
          width: 75,
          height: 5,
          background: '#ce9852',
        }}
      />
      <svg
        width="1720"
        height="650"
        viewBox="0 0 1720 650"
        style={{ position: 'absolute', left: 100, top: 220 }}
      >
        {spec.setting === 'living_room' && (
          <>
            <path d="M0,495 h1720" stroke="#d7d0be" strokeWidth="3" />
            <rect x="0" y="497" width="1720" height="153" fill="#e8dcca" />
            <path d="M0,548 h1720 M0,600 h1720" stroke="#d8ccb9" strokeWidth="2" />
            <rect x="770" y="24" width="940" height="420" rx="25" fill="#fffaf2" opacity=".65" />
          </>
        )}
        {spec.setting === 'desktop' && (
          <>
            <rect x="0" y="500" width="1720" height="35" rx="12" fill="#bc977b" />
            <path d="M130,535 v110 M1590,535 v110" stroke="#8f7565" strokeWidth="18" />
          </>
        )}
        {spec.connections.map((link) => (
          <Connection
            key={link.id}
            link={link}
            objects={spec.objects}
            events={events}
            frame={frame}
          />
        ))}
        {spec.objects.map((o) => (
          <ObjectShape
            key={o.id}
            o={o}
            frame={frame}
            events={events}
            renderScreen={renderScreen}
            objectLabel={objectLabel}
          />
        ))}
      </svg>
      <div
        style={{
          position: 'absolute',
          left: 100,
          right: 100,
          bottom: 160,
          display: 'flex',
          gap: 24,
          fontSize: 23,
          color: '#526b79',
        }}
      >
        {[...new Set(events.filter((e) => e.action === 'signal').map((e) => e.channel))].map(
          (c) => (
            <span key={c}>
              <span
                style={{
                  display: 'inline-block',
                  width: 12,
                  height: 12,
                  borderRadius: 6,
                  background: colors[c],
                  marginRight: 9,
                }}
              />
              {{ video: '图像信号', audio: '音频信号', control: '控制指令', data: '数据' }[c]}
            </span>
          ),
        )}
      </div>
    </AbsoluteFill>
  );
}
export function ObjectSceneSounds({
  scene,
  fps = 30,
  preview = false,
}: {
  scene: Scene;
  fps?: number;
  preview?: boolean;
}) {
  if (preview || !scene.visual_scene?.sound_enabled) return null;
  return (
    <>
      {(scene.compiled_object_events || [])
        .filter((e) => e.sound)
        .map((e) => (
          <Sequence
            key={e.id}
            from={e.start_frame}
            durationInFrames={Math.min(Math.round(0.5 * fps), scene.frames - e.start_frame)}
          >
            <Audio
              src={staticFile(`scene-sfx-${e.sound}.wav`)}
              volume={scene.visual_scene!.sound_volume}
            />
          </Sequence>
        ))}
    </>
  );
}
