// Fixed repository-owned verifier. Never run arbitrary user/model TSX on host.
import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { SceneRenderer } from './semantic-kit';
import type { VideoProps } from './contracts';
export default function IllustratedFixture(props: VideoProps) {
  return (
    <AbsoluteFill>
      {props.scenes.map((scene) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          <SceneRenderer scene={scene} assets={props.generated_assets} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
