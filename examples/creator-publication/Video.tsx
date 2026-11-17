import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame } from 'remotion';
import type { VideoProps } from './contracts';

function Example() {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: '#eef5f7', color: '#163b3b', padding: 110}}>
    <h1 style={{fontSize: 60, margin: '40px 0 100px'}}>同一段文稿，检查两个维度</h1>
    <div style={{display: 'flex', gap: 50}}>{['音色是否合适', '表达是否到位'].map((text, index) =>
      <div key={text} style={{width: 730, padding: 60, background: '#fff', fontSize: 48, borderRadius: 20, border: '2px solid #8bb7b5', transform: `translateY(${Math.sin(frame / 18 + index) * 6}px)`}}>{text}</div>
    )}</div>
  </AbsoluteFill>;
}

// Fixed authored silent fixture. It exercises presentation; it is not a model output.
export default function Video(props: VideoProps) {
  return <AbsoluteFill>{props.scenes.map((scene) => <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}><Example /></Sequence>)}</AbsoluteFill>;
}
