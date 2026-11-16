// Fixed, authored repository showcase. This is not a native-Agent inference result.
import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import type { Scene, VideoProps } from './contracts';
import { MotionScene, designPacks, motionProgress } from './motion-kit';

type IntroMeta = {
  waveforms: Record<string, number[]>;
  source_files: number;
  recording_start: number;
};
const P = designPacks.editorial_warm;
const ease = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: (t) => 1 - Math.pow(1 - t, 3),
  });
const mono: React.CSSProperties = { fontFamily: 'monospace' };
const box: React.CSSProperties = {
  background: P.panel,
  border: '2px solid #d9ddd4',
  borderRadius: 20,
};
function Pill({ children, accent = false }: { children: React.ReactNode; accent?: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '9px 18px',
        borderRadius: 30,
        background: accent ? '#a63d4912' : '#273b380a',
        fontSize: 20,
        color: accent ? P.accent : P.ink,
      }}
    >
      {children}
    </span>
  );
}
function Frame({ scene, children }: { scene: Scene; children: React.ReactNode }) {
  return (
    <AbsoluteFill style={{ background: P.background, color: P.ink }}>
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 65,
          fontSize: 18,
          letterSpacing: 3,
          color: P.muted,
        }}
      >
        ENGINEERING VIDEO AGENT / 项目介绍
      </div>
      <div style={{ position: 'absolute', left: 100, top: 115, fontSize: 48, fontWeight: 700 }}>
        {scene.title}
      </div>
      {children}
    </AbsoluteFill>
  );
}
function Intro({ scene }: { scene: Scene }) {
  const f = useCurrentFrame();
  const cover = 1 - ease(f, 75, 105);
  return (
    <>
      <MotionScene scene={scene} designPack="editorial_warm" />
      <div
        style={{ position: 'absolute', top: 860, left: 100, right: 100, display: 'flex', gap: 18 }}
      >
        <Pill>源码依据</Pill>
        <Pill>分镜与动效</Pill>
        <Pill>编译与检查</Pill>
        <Pill accent>视频 + 可编辑工程</Pill>
      </div>
      {cover > 0 && (
        <AbsoluteFill
          style={{
            background: P.background,
            opacity: cover,
            justifyContent: 'center',
            padding: 110,
          }}
        >
          <div style={{ fontSize: 20, letterSpacing: 4, color: P.muted, marginBottom: 30 }}>
            ENGINEERING VIDEO AGENT
          </div>
          <div
            style={{
              fontSize: 92,
              fontWeight: 700,
              lineHeight: 1.35,
              transform: `translateY(${20 * (1 - ease(f, 0, 30))}px)`,
            }}
          >
            从项目源码
            <br />到<span style={{ color: P.accent }}>可编辑的讲解视频</span>
          </div>
          <div
            style={{ display: 'flex', alignItems: 'center', gap: 24, marginTop: 55, fontSize: 27 }}
          >
            <Pill>输入源码 / 想法</Pill>
            <span>→</span>
            <Pill accent>讲清楚 · 能修改 · 可复现</Pill>
          </div>
        </AbsoluteFill>
      )}
    </>
  );
}
function Visual({ scene }: { scene: Scene }) {
  return (
    <>
      <MotionScene scene={scene} designPack="editorial_warm" />
      <div
        style={{
          position: 'absolute',
          top: 850,
          left: 100,
          right: 100,
          textAlign: 'center',
          fontSize: 26,
          color: P.muted,
        }}
      >
        选择表达机制，再组织对象、关系与变化。
      </div>
    </>
  );
}
function Timing({ scene, meta }: { scene: Scene; meta: IntroMeta }) {
  const f = useCurrentFrame();
  const samples = meta.waveforms[scene.id] || [];
  const ratio = f / scene.frames;
  return (
    <Frame scene={scene}>
      <div
        style={{ position: 'absolute', left: 100, right: 100, top: 245, display: 'flex', gap: 40 }}
      >
        {['语音', '词时间戳', '帧事件'].map((label, i) => (
          <div
            key={label}
            style={{
              ...box,
              padding: '32px 40px',
              width: 545,
              opacity: ease(f, i * 7, i * 7 + 18),
            }}
          >
            <div style={{ fontSize: 18, color: P.accent, marginBottom: 18 }}>0{i + 1}</div>
            <div style={{ fontSize: 34, fontWeight: 700, marginBottom: 12 }}>{label}</div>
            <div style={{ fontSize: 22, color: P.muted }}>
              {
                ['Edge 云希 · 普通话男声', '来自实际语音服务的时间边界', '词语出现 → 组件状态变化'][
                  i
                ]
              }
            </div>
          </div>
        ))}
      </div>
      <svg
        style={{ position: 'absolute', left: 100, top: 485 }}
        width="1720"
        height="255"
        viewBox="0 0 1720 255"
      >
        <rect width="1720" height="255" rx="20" fill={P.panel} />
        {samples
          .filter((_, i) => i % 3 === 0)
          .map((v, i) => (
            <rect
              key={i}
              x={30 + i * 8.25}
              y={125 - v * 90}
              width="4"
              height={Math.max(3, v * 180)}
              rx="2"
              fill={(i * 3) / samples.length < ratio ? P.accent : '#bcc9c2'}
            />
          ))}
        <line
          x1={30 + ratio * 1655}
          x2={30 + ratio * 1655}
          y1="20"
          y2="225"
          stroke={P.ink}
          strokeWidth="3"
        />
      </svg>
      <div style={{ position: 'absolute', top: 780, left: 100, fontSize: 25, color: P.ink }}>
        实测波形 · 原生词边界 · 非等分时间轴
      </div>
      <div style={{ position: 'absolute', top: 840, left: 100, fontSize: 21, color: P.muted }}>
        旁白原句说明 Qwen 架构；本样片实际使用 Edge，不代表 Whisper 或 Qwen 部署验收。
      </div>
    </Frame>
  );
}
function Studio({ scene, meta }: { scene: Scene; meta: IntroMeta }) {
  const f = useCurrentFrame();

  return (
    <Frame scene={scene}>
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 225,
          width: 1720,
          height: 650,
          ...box,
          overflow: 'hidden',
          boxShadow: '0 20px 50px #273b3810',
        }}
      >
        <OffthreadVideo
          src={staticFile('workbench.webm')}
          playbackRate={1.25}
          startFrom={meta.recording_start}
          muted
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center' }}
        />
        {f < 50 && (
          <Img
            src={staticFile('input.png')}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: 'top',
              opacity: 1 - ease(f, 20, 50),
            }}
          />
        )}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            right: 20,
            padding: '8px 15px',
            background: '#273b38ed',
            borderRadius: 8,
            color: 'white',
            fontSize: 18,
          }}
        >
          实际工作台录制 · 显式模板 / 脚本模式
        </div>
      </div>
      <div style={{ position: 'absolute', top: 885, left: 105, fontSize: 20, color: P.muted }}>
        真实上传本项目源码 · {meta.source_files} 个文本文件 · 编辑动效 → 新版本 → 版本差异
      </div>
    </Frame>
  );
}
function Gates({ scene }: { scene: Scene }) {
  const f = useCurrentFrame();
  const labels = ['编译', '试渲染', '检查', '交付'];
  return (
    <Frame scene={scene}>
      <div
        style={{ position: 'absolute', left: 100, right: 100, top: 315, display: 'flex', gap: 34 }}
      >
        {labels.map((label, i) => {
          const t = motionProgress(scene, `gate${i}`, f, 'reveal', 0);
          return (
            <div
              key={label}
              style={{
                ...box,
                width: 405,
                height: 270,
                padding: 32,
                opacity: 0.25 + 0.75 * t,
                transform: `translateY(${22 * (1 - t)}px)`,
                borderColor: t > 0.5 ? '#78958c' : '#d9ddd4',
              }}
            >
              <div style={{ fontSize: 20, color: P.accent, marginBottom: 28 }}>0{i + 1}</div>
              <div style={{ fontSize: 40, fontWeight: 700 }}>{label}</div>
              <div style={{ fontSize: 20, color: P.muted, marginTop: 22 }}>
                {
                  [
                    'TypeScript + Bundle',
                    '关键帧 + 连续镜头',
                    '元数据 + 实际解码',
                    'MP4 + 完整源码',
                  ][i]
                }
              </div>
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 100,
          right: 100,
          top: 680,
          height: 80,
          ...box,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 28,
        }}
      >
        代码 / 音轨 / 素材改变<span style={{ color: P.accent, padding: '0 25px' }}>→</span>
        旧审查失效，重新构建与预览
      </div>
      <div style={{ position: 'absolute', top: 835, left: 100, fontSize: 21, color: P.muted }}>
        本片为固定编排的真实渲染测试；编译成功不等于模型自动生成质量通过。
      </div>
    </Frame>
  );
}
function Delivery({ scene }: { scene: Scene }) {
  const f = useCurrentFrame();
  return (
    <Frame scene={scene}>
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 270,
          width: 900,
          height: 550,
          ...box,
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(145deg,#143735,#34574f)',
          }}
        />
        <div
          style={{
            position: 'relative',
            color: '#f9f4e8',
            padding: 60,
            fontSize: 57,
            lineHeight: 1.4,
            fontWeight: 700,
          }}
        >
          让复杂内容
          <br />
          成为<span style={{ color: '#e5b69d' }}>清楚的讲解</span>
          <div style={{ fontSize: 19, letterSpacing: 5, marginTop: 35, fontWeight: 400 }}>
            4K / 30 FPS / EDITABLE
          </div>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 1070, top: 270, width: 750 }}>
        {[
          ['MP4', '4K 介绍视频'],
          ['WAV / SRT', '旁白与实际时间轴'],
          ['TSX / ZIP', 'Remotion 可编辑工程'],
          ['MD / JSON', '分析、证据与验收报告'],
        ].map(([ext, text], i) => (
          <div
            key={ext}
            style={{
              ...box,
              marginBottom: 18,
              padding: '21px 26px',
              display: 'flex',
              alignItems: 'center',
              gap: 28,
              opacity: ease(f, i * 13, i * 13 + 20),
              transform: `translateX(${35 * (1 - ease(f, i * 13, i * 13 + 20))}px)`,
            }}
          >
            <span style={{ ...mono, width: 150, fontSize: 25, color: P.accent }}>{ext}</span>
            <span style={{ fontSize: 25 }}>{text}</span>
          </div>
        ))}
      </div>
    </Frame>
  );
}
function Boundary({ scene }: { scene: Scene }) {
  const f = useCurrentFrame();
  return (
    <Frame scene={scene}>
      <div
        style={{ position: 'absolute', left: 100, top: 260, right: 100, display: 'flex', gap: 45 }}
      >
        {[
          [
            '已实测',
            '#456c5c',
            ['本项目源码导入与编辑', 'Edge 男声 + 实际词时间戳', 'Remotion 编译、预览与 4K 渲染'],
          ],
          [
            '待部署与验收',
            P.accent,
            ['Codex / Claude 真实模型推理', 'Docker / gVisor 隔离执行', '整片连续观看与人工试听'],
          ],
        ].map(([title, color, items], i) => (
          <div
            key={String(title)}
            style={{
              ...box,
              width: 837,
              padding: '35px 40px',
              height: 390,
              opacity: ease(f, i * 12, i * 12 + 22),
            }}
          >
            <div style={{ fontSize: 33, color: String(color), fontWeight: 700, marginBottom: 30 }}>
              {title as string}
            </div>
            {(items as string[]).map((item) => (
              <div key={item} style={{ fontSize: 26, lineHeight: 2.1 }}>
                · {item}
              </div>
            ))}
          </div>
        ))}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 100,
          right: 100,
          top: 735,
          fontSize: 43,
          fontWeight: 700,
          textAlign: 'center',
          opacity: ease(f, 90, 120),
        }}
      >
        讲得清楚，改得动，过程可复现。
      </div>
      <div
        style={{
          position: 'absolute',
          top: 830,
          left: 100,
          right: 100,
          textAlign: 'center',
          fontSize: 20,
          color: P.muted,
        }}
      >
        本片不是“任意源码一键生成”的完整验收。
      </div>
    </Frame>
  );
}
function Shot({ scene, meta }: { scene: Scene; meta: IntroMeta }) {
  const f = useCurrentFrame();
  const opacity = Math.min(ease(f, 0, 12), 1 - ease(f, scene.frames - 10, scene.frames));
  let body: React.ReactNode;
  switch (scene.id) {
    case 'intro':
      body = <Intro scene={scene} />;
      break;
    case 'visual':
      body = <Visual scene={scene} />;
      break;
    case 'timing':
      body = <Timing scene={scene} meta={meta} />;
      break;
    case 'studio':
      body = <Studio scene={scene} meta={meta} />;
      break;
    case 'gates':
      body = <Gates scene={scene} />;
      break;
    case 'delivery':
      body = <Delivery scene={scene} />;
      break;
    default:
      body = <Boundary scene={scene} />;
  }
  return (
    <AbsoluteFill style={{ opacity }}>
      {body}
      <div style={{ position: 'absolute', right: 100, top: 62, fontSize: 17, color: P.muted }}>
        工程能力验证 / 固定编排
      </div>
    </AbsoluteFill>
  );
}
export default function EngineeringVideo(props: VideoProps) {
  const frame = useCurrentFrame();
  const meta = (props as VideoProps & { intro_meta: IntroMeta }).intro_meta;
  return (
    <AbsoluteFill style={{ background: P.background }}>
      {props.scenes.map((s) => (
        <Sequence key={s.id} from={s.start_frame} durationInFrames={s.frames}>
          <Shot scene={s} meta={meta} />
        </Sequence>
      ))}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          height: 5,
          width: `${(100 * frame) / props.total_frames}%`,
          background: P.accent,
        }}
      />
    </AbsoluteFill>
  );
}
