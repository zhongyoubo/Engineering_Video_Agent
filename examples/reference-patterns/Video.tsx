import React from 'react';
import { Sequence } from 'remotion';
import { MotionScene } from './motion-kit';
import type { VideoProps } from './contracts';

// Authored visual fixture, not a model-generated or narrated production sample.
export default function ReferencePatterns(props: VideoProps) {
  return (
    <>
      {props.scenes.map((scene) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          <MotionScene scene={scene} designPack={props.design_pack || 'editorial_warm'} />
        </Sequence>
      ))}
    </>
  );
}
