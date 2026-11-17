import React, { useEffect, useState } from 'react';
import {
  AbsoluteFill,
  Audio,
  Composition,
  Sequence,
  cancelRender,
  continueRender,
  delayRender,
  getInputProps,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import EngineeringVideo from './Video';
import { Bookend, PublicationThumbnail, ViewerDisclosures } from './presentation';
import type { VideoProps, Scene } from './contracts';

function Caption({ scene }: { scene: Scene }) {
  const frame = useCurrentFrame();
  const cue = scene.cues.find((c) => c.start <= frame / 30 && c.end > frame / 30);
  if (!cue) return null;
  return (
    <div
      data-caption
      style={{
        position: 'absolute',
        bottom: 44,
        left: 100,
        right: 100,
        textAlign: 'center',
        fontSize: 30,
        lineHeight: 1.5,
        color: '#172c49',
      }}
    >
      <span
        style={{
          display: 'inline-block',
          padding: '10px 22px',
          borderRadius: 12,
          background: '#f5f8fbd9',
          whiteSpace: 'pre-wrap',
        }}
      >
        {cue.text}
      </span>
    </div>
  );
}
function TrustedVideo(props: VideoProps) {
  const [handle] = useState(() => delayRender('required CJK font'));
  useEffect(() => {
    const face = new FontFace('EngineeringNoto', `url(${staticFile('noto.otf')})`);
    face
      .load()
      .then((font) => {
        document.fonts.add(font);
        if (!document.fonts.check('24px EngineeringNoto'))
          throw new Error('Required font not ready');
        continueRender(handle);
      })
      .catch((error) => cancelRender(error));
  }, [handle]);
  return (
    <AbsoluteFill
      style={{
        fontFamily: 'EngineeringNoto, sans-serif',
        background: '#f5f8fc',
        width: 1920,
        height: 1080,
        transform: `scale(${(props.width || 1920) / 1920})`,
        transformOrigin: 'top left',
      }}
    >
      <EngineeringVideo {...props} />
      {props.scenes.map((scene) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          {(props.presentation_profile || 'creator') === 'creator' &&
            (scene.role === 'opening' || scene.role === 'closing') && (
              <Bookend scene={scene} props={props} />
            )}
          <ViewerDisclosures scene={scene} fps={props.fps} />
          {scene.audio_src && <Audio src={staticFile(scene.audio_src)} />}
          <Caption scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
export function Root() {
  const props = getInputProps() as unknown as VideoProps;
  return (
    <>
      <Composition
        id="EngineeringVideo"
        component={TrustedVideo}
        width={props.width || 1920}
        height={props.height || 1080}
        fps={props.fps || 30}
        durationInFrames={props.total_frames}
        defaultProps={props}
      />
      <Composition
        id="PublicationThumbnail"
        component={PublicationThumbnail}
        width={props.width || 1920}
        height={props.height || 1080}
        fps={30}
        durationInFrames={1}
        defaultProps={props}
      />
    </>
  );
}
