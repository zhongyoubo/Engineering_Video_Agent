/** Adapted from lifeprompt-team/remotion-scenes; MIT. See LICENSE.txt / ADAPTATIONS.md. */
import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

type TextProps = {
  text: string;
  startFrame?: number;
  color?: string;
  accent?: string;
  fontSize?: number;
};

/** Transparent, layout-independent typing; frame-driven and safe for CJK/code points. */
export function PackTypewriter({
  text,
  startFrame = 0,
  color = '#18364b',
  accent = '#ed775a',
  fontSize = 64,
}: TextProps) {
  const frame = useCurrentFrame();
  const chars = Array.from(text);
  const n = Math.max(0, Math.min(chars.length, Math.floor((frame - startFrame) / 3)));
  return (
    <div
      style={{
        fontFamily: 'EngineeringNoto, sans-serif',
        fontSize,
        color,
        whiteSpace: 'pre-wrap',
        lineHeight: 1.35,
      }}
    >
      {chars.slice(0, n).join('')}
      <span
        style={{
          color: accent,
          opacity:
            frame >= startFrame && n < chars.length && Math.floor(frame / 12) % 2 === 0 ? 1 : 0,
        }}
      >
        ▎
      </span>
    </div>
  );
}

/** Staggered spring arrival settles to a held result; no perpetual distracting bounce. */
export function PackKinetic({
  text,
  startFrame = 0,
  color = '#18364b',
  accent = '#ed775a',
  fontSize = 72,
}: TextProps) {
  const frame = useCurrentFrame(),
    { fps } = useVideoConfig();
  return (
    <div
      style={{
        fontFamily: 'EngineeringNoto, sans-serif',
        fontSize,
        fontWeight: 800,
        color,
        whiteSpace: 'pre-wrap',
        lineHeight: 1.4,
      }}
    >
      {Array.from(text).map((c, i) => {
        const p = spring({
          frame: frame - startFrame - i * 3,
          fps,
          config: { damping: 16, stiffness: 170, mass: 0.8 },
        });
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: Math.min(1, p),
              transform: `translateY(${interpolate(p, [0, 1], [70, 0])}px) scale(${p})`,
              color: i % 4 === 0 ? accent : color,
            }}
          >
            {c === ' ' ? '\u00a0' : c}
          </span>
        );
      })}
    </div>
  );
}
