// Fixed repository verification dispatcher. Never accepts uploaded/model TSX.
import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { SceneRenderer } from './semantic-kit';
import { MotionScene } from './motion-kit';
import type { VideoProps } from './contracts';
export default function ReferenceMechanisms(props: VideoProps) {
  return (
    <AbsoluteFill>
      {props.scenes.map((scene) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          {scene.semantic_scene ? (
            <SceneRenderer scene={scene} assets={props.generated_assets} />
          ) : (
            <MotionScene scene={scene} designPack={props.design_pack} />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
