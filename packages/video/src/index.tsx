import React from 'react';
import { Composition, registerRoot } from 'remotion';
import { Video } from './Video';
import type { VideoProps } from './types';
const defaults: VideoProps = {
  schema_version: '1.0',
  title: 'Explainer Studio',
  language: 'zh-CN',
  accent: 'blue',
  audience: 'general',
  scenes: [],
  fps: 30,
  width: 1920,
  height: 1080,
  total_frames: 30,
  notices: [],
  audio_alignment: 'none',
};
const Root = () => (
  <Composition
    id="ExplainerVideo"
    component={Video}
    durationInFrames={30}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={defaults}
    calculateMetadata={({ props }) => ({
      durationInFrames: props.total_frames,
      width: props.width,
      height: props.height,
      fps: props.fps,
    })}
  />
);
registerRoot(Root);
