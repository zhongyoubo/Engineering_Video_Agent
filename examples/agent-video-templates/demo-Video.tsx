import React from 'react';
import {AbsoluteFill,Sequence} from 'remotion';
import {DarkEditorial} from './DarkEditorial';
import {WarmIllustrated} from './WarmIllustrated';
import type {VideoProps} from './contracts';

export default function Video(props:VideoProps){
  return <AbsoluteFill>{props.scenes.map(scene=><Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
    {scene.id==='parts'?<WarmIllustrated slide={{eyebrow:'AI AGENT / 入门解释',title:'一个 Agent 包含什么？',subtitle:'把它想象成一个数字员工。',items:[
      {title:'大模型',detail:'理解与判断',icon:'gear'}, {title:'记忆',detail:'工作档案',icon:'file'}, {title:'工具',detail:'执行操作',icon:'work'},
      {title:'规划',detail:'任务步骤',icon:'calendar'}, {title:'观察',detail:'结果检查',icon:'search'}, {title:'权限',detail:'安全边界',icon:'shield'},
    ]}}/>:<DarkEditorial slide={{eyebrow:'AI AGENT / 入门解释',title:'什么是 AI Agent？',leftLabel:'AI Agent',highlight:'到底是什么？',description:'用一个生活中的任务，讲清楚它怎么工作。',leftCaption:'回答问题',rightCaption:'完成任务',rightLabel:'概念定义'}}/>}
  </Sequence>)}</AbsoluteFill>;
}
