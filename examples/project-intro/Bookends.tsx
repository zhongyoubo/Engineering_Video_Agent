// Authored assembly. The body is a verified local video asset, with its original source delivered separately.
import React from 'react';
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile } from 'remotion';
import type { VideoProps } from './contracts';
import { CoverScene, EndScene } from './motion-kit';
export default function BookendedIntroduction(props: VideoProps) {
  return (
    <AbsoluteFill>
      {props.scenes.map((scene) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          {scene.id === 'cover' ? (
            <CoverScene />
          ) : scene.id === 'outro' ? (
            <EndScene />
          ) : (
            <OffthreadVideo src={staticFile('body.mp4')} />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
