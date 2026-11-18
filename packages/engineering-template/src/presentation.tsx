import React, { useEffect, useState } from 'react';
import {
  AbsoluteFill,
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import type { Scene, VideoProps } from './contracts';
import { SceneRenderer } from './semantic-kit';

export function PublicationCard({
  headline,
  subtitle = '',
  brand = '',
  closing = false,
  warm = false,
}: {
  headline: string;
  subtitle?: string;
  brand?: string;
  closing?: boolean;
  warm?: boolean;
}) {
  const frame = useCurrentFrame();
  const ink = closing ? '#f7f5ec' : '#163b3b';
  const accent = closing ? '#eec17b' : '#087f83';
  return (
    <AbsoluteFill
      data-publication-card
      style={{
        background: closing ? '#153f40' : warm ? '#f8f3e9' : '#eef5f7',
        color: ink,
        padding: 100,
      }}
    >
      {brand && <div style={{ fontSize: 25, letterSpacing: 2, opacity: 0.75 }}>{brand}</div>}
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 240,
          width: 1120,
          fontSize: headline.length > 60 ? 52 : headline.length > 40 ? 64 : 82,
          fontWeight: 750,
          lineHeight: 1.3,
          overflowWrap: 'anywhere',
        }}
      >
        {headline}
      </div>
      {subtitle && (
        <div
          style={{
            position: 'absolute',
            left: 100,
            top: 660,
            width: 1100,
            fontSize: 32,
            lineHeight: 1.5,
            opacity: 0.85,
          }}
        >
          {subtitle}
        </div>
      )}
      <svg
        aria-hidden="true"
        width="510"
        height="550"
        viewBox="0 0 510 550"
        style={{ position: 'absolute', right: 80, top: 220 }}
      >
        <circle
          cx="255"
          cy="260"
          r="220"
          fill="none"
          stroke={accent}
          strokeOpacity="0.2"
          strokeWidth="2"
        />
        {Array.from({ length: 19 }, (_, i) => {
          const height = 40 + 125 * (0.5 + 0.5 * Math.sin(i * 0.8 + frame / 24));
          return (
            <rect
              key={i}
              x={40 + i * 23}
              y={260 - height / 2}
              width="9"
              height={height}
              rx="4.5"
              fill={accent}
              opacity={0.45 + i / 40}
            />
          );
        })}
      </svg>
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 195,
          width: 80,
          height: 5,
          background: accent,
        }}
      />
    </AbsoluteFill>
  );
}

export function ViewerDisclosures({ scene, fps = 30 }: { scene: Scene; fps?: number }) {
  const seconds = useCurrentFrame() / fps;
  const visible = (scene.disclosures || []).filter(
    (d) => seconds >= d.start_seconds && seconds < d.end_seconds,
  );
  if (!visible.length) return null;
  return (
    <div
      data-viewer-disclosure
      style={{
        position: 'absolute',
        top: 55,
        right: 100,
        maxWidth: 700,
        fontSize: 22,
        color: '#173e42',
        background: '#f6faf8ee',
        borderRadius: 9,
        padding: '10px 18px',
      }}
    >
      {visible.map((d) => d.text).join(' · ')}
    </div>
  );
}

export function Bookend({ scene, props }: { scene: Scene; props: VideoProps }) {
  const closing = scene.role === 'closing';
  return (
    <PublicationCard
      headline={closing ? scene.title : props.cover?.headline || scene.title}
      subtitle={
        closing ? scene.message || scene.bullets.slice(0, 2).join(' · ') : props.cover?.subtitle
      }
      brand={props.creator_brand}
      closing={closing}
      warm={props.design_pack === 'editorial_warm'}
    />
  );
}

/** Independent publish thumbnail; it does not render arbitrary Agent components. */
export function PublicationThumbnail(props: VideoProps) {
  const [handle] = useState(() => delayRender('thumbnail CJK font'));
  useEffect(() => {
    const face = new FontFace('PublicationNoto', `url(${props.fontSrc || staticFile('noto.otf')})`);
    face
      .load()
      .then((font) => {
        (document.fonts as unknown as { add(font: FontFace): void }).add(font);
        continueRender(handle);
      })
      .catch(cancelRender);
  }, [handle, props.fontSrc]);
  return (
    <AbsoluteFill
      style={{
        width: 1920,
        height: 1080,
        fontFamily: 'PublicationNoto, sans-serif',
        transform: `scale(${(props.width || 1920) / 1920})`,
        transformOrigin: 'top left',
      }}
    >
      {props.scenes[0]?.visual_scene || props.scenes[0]?.semantic_scene ? (
        <>
          <SceneRenderer
            assets={props.generated_assets}
            scene={props.scenes[0]}
            frameOverride={Math.max(0, props.scenes[0].frames - 15)}
            titleOverride={props.cover?.headline || props.title}
          />
          {props.cover?.subtitle && (
            <div
              style={{
                position: 'absolute',
                left: 100,
                bottom: 85,
                fontSize: 30,
                color: '#294b56',
              }}
            >
              {props.cover.subtitle}
            </div>
          )}
        </>
      ) : (
        <PublicationCard
          headline={props.cover?.headline || props.title}
          subtitle={props.cover?.subtitle}
          brand={props.creator_brand}
          warm={props.design_pack === 'editorial_warm'}
        />
      )}
    </AbsoluteFill>
  );
}
