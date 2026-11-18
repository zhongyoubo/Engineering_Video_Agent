// Fixed repository-authored verification dispatcher, never loaded from a user path.
import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { ObjectScene } from './scene-objects';
import type { VideoProps } from './contracts';
export default function ObjectFixture(props: VideoProps) {
  return (
    <AbsoluteFill>
      {props.scenes.map((scene) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          <ObjectScene scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
