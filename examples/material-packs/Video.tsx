// Fixed reviewed integration fixture; never an entry point for user/model source.
import React from 'react';
import { AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion';
import {
  PackBookOpen,
  PackBrain,
  PackRobot,
  PackTerminal,
  PackFolder,
  PackMagnifyingGlass,
  PackGear,
  PackMonitor,
} from './vendor/phosphor/Icons';
import { PackTypewriter, PackKinetic } from './vendor/motion/MotionText';
import { LibraryModel } from './library-model';
import type { VideoProps } from './contracts';

const icons = [
  PackBookOpen,
  PackBrain,
  PackRobot,
  PackTerminal,
  PackFolder,
  PackMagnifyingGlass,
  PackGear,
  PackMonitor,
];
const labels = [
  '学习资料',
  '理解问题',
  '行动助手',
  '执行命令',
  '整理文件',
  '查找依据',
  '使用工具',
  '查看结果',
];
const colors = [
  '#c66938',
  '#8972ac',
  '#298c83',
  '#386d9f',
  '#b68a2c',
  '#b55868',
  '#588d49',
  '#477c9b',
];
function Frame({ index, assets }: { index: number; assets: Record<string, string> }) {
  const f = useCurrentFrame();
  const enter = (delay: number) =>
    interpolate(f, [delay, delay + 20], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  const backgrounds = ['#faf3e4', '#edf5ef', '#edf1fb', '#1a282c'];
  const ink = index === 3 ? '#f3efd9' : '#244856';
  const headings = [
    '让抽象概念，有可辨认的对象',
    '用熟悉的物品，联系日常经验',
    '把问题说具体，把结果留下来',
    '同一个物体，换个角度看',
  ];
  return (
    <AbsoluteFill style={{ background: backgrounds[index], color: ink, padding: '86px 105px' }}>
      <div style={{ fontSize: 25, letterSpacing: 3, color: index === 3 ? '#9dc1b1' : '#788b89' }}>
        从理解，到表达
      </div>
      <h1 style={{ marginTop: 20, fontSize: 64, fontWeight: 700 }}>{headings[index]}</h1>
      {index === 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4,1fr)',
            gap: '42px 70px',
            marginTop: 72,
          }}
        >
          {icons.map((Icon, i) => (
            <div
              key={i}
              style={{
                textAlign: 'center',
                opacity: enter(i * 6),
                transform: `translateY(${(1 - enter(i * 6)) * 40}px)`,
              }}
            >
              <Icon size={175} color={colors[i]} />
              <div style={{ fontSize: 32, marginTop: 12 }}>{labels[i]}</div>
            </div>
          ))}
        </div>
      )}
      {index === 1 && (
        <>
          <Img
            src={staticFile(assets.notebook)}
            style={{
              position: 'absolute',
              left: 130,
              top: 320,
              width: 540,
              height: 540,
              objectFit: 'contain',
              transform: `translateY(${(1 - enter(4)) * 80}px) rotate(${(1 - enter(4)) * -12}deg)`,
            }}
          />
          <div style={{ position: 'absolute', left: 900, top: 370, fontSize: 48, lineHeight: 1.7 }}>
            <b>一本笔记本</b>
            <div>记录 → 整理 → 回顾</div>
            <p style={{ fontSize: 30, color: '#738d82' }}>从你已经认识的事物开始</p>
          </div>
          <Img
            src={staticFile(assets.bubble)}
            style={{ position: 'absolute', left: 1400, top: 660, width: 220, opacity: enter(30) }}
          />
          <Img
            src={staticFile(assets.heart)}
            style={{ position: 'absolute', left: 1320, top: 750, width: 100, opacity: enter(50) }}
          />
        </>
      )}
      {index === 2 && (
        <div style={{ position: 'absolute', left: 140, right: 140, top: 360 }}>
          <div style={{ fontSize: 27, color: '#7987a5', marginBottom: 30 }}>你可以这样提问</div>
          <PackTypewriter
            text="帮我把这段话，改得更容易懂。"
            startFrame={0}
            fontSize={64}
            color="#355a80"
            accent="#d8755b"
          />
          <div style={{ marginTop: 110 }}>
            <PackKinetic
              text="说清目标，补上背景"
              startFrame={45}
              fontSize={70}
              color="#355a80"
              accent="#d8755b"
            />
          </div>
        </div>
      )}
      {index === 3 && (
        <>
          <div style={{ position: 'absolute', left: 170, top: 300, width: 800, height: 670 }}>
            <LibraryModel
              asset={assets.avocado}
              angle={interpolate(f, [0, 110], [0, Math.PI * 1.5], { extrapolateRight: 'clamp' })}
              width={800}
              height={670}
            />
          </div>
          <div
            style={{ position: 'absolute', left: 1120, top: 440, fontSize: 42, lineHeight: 1.8 }}
          >
            <div style={{ color: '#bbd8a5', fontSize: 58 }}>观察一个牛油果</div>
            <div>形状 · 颜色 · 切面</div>
            <div style={{ fontSize: 28, color: '#9fb5ad', marginTop: 24 }}>
              多角度观察，补充理解
            </div>
          </div>
        </>
      )}
    </AbsoluteFill>
  );
}
export default function MaterialPackFixture(props: VideoProps) {
  return (
    <AbsoluteFill>
      {props.scenes.map((scene, i) => (
        <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.frames}>
          <Frame index={i} assets={props.generated_assets || {}} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
