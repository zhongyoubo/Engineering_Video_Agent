/** Protected frame-driven spatial vocabulary. Registered images only; no provider calls. */
import React, { useLayoutEffect, useMemo, useRef } from 'react';
import { Img, staticFile, useVideoConfig } from 'remotion';
import { ThreeCanvas } from '@remotion/three';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';
import type { Scene } from './contracts';
import type { SemanticEntity, SpatialSpec } from './semantic-types';
import { parameterValue } from './mechanism-kit';
import { useTheme } from './theme';
import {
  cameraPose,
  cityBuildings,
  clamp01,
  matrixState,
  networkGeometry,
  propagationState,
  seeded,
  smooth,
} from './spatial-state';

function normalized(scene: Scene, id: string, frame: number) {
  const p = scene.semantic_scene?.parameters?.find((p) => p.id === id);
  if (!p) throw Error('Missing spatial parameter');
  return clamp01((parameterValue(scene, id, frame) - p.minimum) / (p.maximum - p.minimum));
}
function Atmosphere({ frame }: { frame: number }) {
  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse at 18% 62%, #b04b7866, transparent 48%), linear-gradient(#0b112a 5%, #312344 46%, #ba637d 66%, #33213f 68%, #100e27 100%)',
        }}
      />
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0 }}
      >
        {Array.from({ length: 110 }, (_, i) => (
          <circle
            key={i}
            cx={seeded(7, i * 2) * 1920}
            cy={seeded(7, i * 2 + 1) * 540}
            r={0.5 + seeded(13, i)}
            fill="#e5deff"
            opacity={0.12 + 0.42 * (0.5 + 0.5 * Math.sin(frame / 38 + i))}
          />
        ))}
        {Array.from({ length: 15 }, (_, i) => (
          <line
            key={`ray-${i}`}
            x1="960"
            y1="705"
            x2={(i - 7) * 260 + 960}
            y2="1080"
            stroke="#df95c2"
            strokeWidth="1"
            opacity="0.1"
          />
        ))}
        {Array.from({ length: 7 }, (_, i) => (
          <line
            key={`h-${i}`}
            x1="0"
            x2="1920"
            y1={720 + i * i * 8}
            y2={720 + i * i * 8}
            stroke="#df95c2"
            opacity="0.1"
          />
        ))}
      </svg>
    </>
  );
}
function Camera({ spec, progress }: { spec: SpatialSpec; progress: number }) {
  const { camera } = useThree(),
    pose = cameraPose(spec, progress);
  useLayoutEffect(() => {
    camera.position.set(...pose.position);
    camera.lookAt(...pose.target);
    camera.updateMatrixWorld();
  }, [camera, pose.position[0], pose.position[1], pose.position[2]]);
  return null;
}
function Buildings({ spec }: { spec: SpatialSpec }) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const buildings = useMemo(() => cityBuildings(spec), [spec.seed, spec.count, spec.columns]);
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#171523';
    ctx.fillRect(0, 0, 128, 256);
    for (let y = 5; y < 256; y += 12)
      for (let x = 5; x < 128; x += 13) {
        const v = seeded(37, y * 128 + x);
        ctx.fillStyle = v > 0.45 ? (v > 0.8 ? '#f8c9a2' : '#9dbcca') : '#292535';
        ctx.fillRect(x, y, 6, 5);
      }
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, []);
  useLayoutEffect(() => {
    if (!mesh.current) return;
    const object = new THREE.Object3D(),
      color = new THREE.Color();
    buildings.forEach((b, i) => {
      object.position.set(b.x, b.height / 2 + 0.1, b.z);
      object.scale.set(b.width, b.height, b.depth);
      object.updateMatrix();
      mesh.current!.setMatrixAt(i, object.matrix);
      mesh.current!.setColorAt(i, color.set(b.color));
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true;
    mesh.current.computeBoundingSphere();
    return () => texture.dispose();
  }, [buildings, texture]);
  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, buildings.length]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial
        map={texture}
        emissiveMap={texture}
        emissive="#e6bed9"
        emissiveIntensity={0.78}
        roughness={0.8}
      />
    </instancedMesh>
  );
}
function City({
  spec,
  progress,
  frame,
  width,
  height,
}: {
  spec: SpatialSpec;
  progress: number;
  frame: number;
  width: number;
  height: number;
}) {
  const output = useVideoConfig();
  const rows = Math.ceil(spec.count / spec.columns),
    landWidth = spec.columns * 2.25 + 4,
    landDepth = rows * 2.25 + 5;
  const shore = useMemo(() => {
    const w = landWidth / 2,
      d = landDepth / 2,
      s = new THREE.Shape();
    s.moveTo(-w - 3, -d - 3);
    s.lineTo(w - 2, -d - 3);
    s.quadraticCurveTo(w + 7, -d - 2, w + 5, -d / 3);
    s.quadraticCurveTo(w + 2, 0, w + 5, d / 2);
    s.quadraticCurveTo(w + 6, d + 5, w - 4, d + 4);
    s.lineTo(-w - 3, d + 4);
    s.closePath();
    return s;
  }, [landWidth, landDepth]);
  return (
    <ThreeCanvas
      width={width}
      height={height}
      dpr={Math.max(1, output.width / 1920)}
      camera={{ fov: 47, near: 0.1, far: 220, position: [25, 18, 25] }}
      gl={{ alpha: true, antialias: true }}
      style={{ position: 'absolute', inset: 0 }}
    >
      <Camera spec={spec} progress={progress} />
      <ambientLight intensity={1.2} />
      <directionalLight position={[-20, 40, 10]} color="#ffc2cc" intensity={2.2} />
      <fog attach="fog" args={['#56304f', 50, 115]} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.14, 0]}>
        <planeGeometry args={[1000, 1000]} />
        <meshStandardMaterial color="#35253f" roughness={0.42} metalness={0.5} />
      </mesh>
      <mesh position={[0, 0.02, -1]} rotation={[-Math.PI / 2, 0, 0]}>
        <shapeGeometry args={[shore, 40]} />
        <meshStandardMaterial color="#18141f" side={THREE.DoubleSide} />
      </mesh>
      <Buildings spec={spec} />
      {Array.from({ length: spec.columns + 1 }, (_, i) => (
        <mesh
          key={`road-x-${i}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[(i - spec.columns / 2) * 2.25, 0.08, -1]}
        >
          <planeGeometry args={[0.34, landDepth]} />
          <meshBasicMaterial color={i % 5 === 0 ? '#624355' : '#25212c'} />
        </mesh>
      ))}
      {Array.from({ length: rows + 1 }, (_, i) => (
        <mesh
          key={`road-z-${i}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, 0.085, (i - rows / 2) * 2.25]}
        >
          <planeGeometry args={[landWidth, 0.32]} />
          <meshBasicMaterial color={i % 4 === 0 ? '#68454c' : '#25212c'} />
        </mesh>
      ))}
      {Array.from({ length: 100 }, (_, i) => {
        const x = ((i % 5) - 2) * 4.5 + 0.12,
          z =
            ((((seeded(41, i) * landDepth + (frame / 90) * (i % 2 ? 1 : -1)) % landDepth) +
              landDepth) %
              landDepth) -
            landDepth / 2;
        return (
          <mesh key={i} position={[x, 0.16, z]}>
            <sphereGeometry args={[0.055, 5, 4]} />
            <meshBasicMaterial color={i % 3 ? '#ffe5af' : '#93e4ec'} toneMapped={false} />
          </mesh>
        );
      })}
      <mesh position={[0, 0.02, landDepth / 2 + 0.5]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[landWidth + 3, 0.08]} />
        <meshBasicMaterial color="#e59bc3" transparent opacity={0.72} />
      </mesh>
    </ThreeCanvas>
  );
}
function Matrix({
  scene,
  entity,
  frame,
  progress,
  assets,
}: {
  scene: Scene;
  entity: SemanticEntity;
  frame: number;
  progress: number;
  assets: Record<string, string>;
}) {
  const spec = entity.spatial!,
    state = matrixState(spec.count, progress / 0.78),
    columns = spec.columns;
  const rows = Math.ceil(spec.count / columns),
    areaW = 1740,
    areaH = 570,
    tileW = areaW / columns,
    tileH = areaH / rows;
  const first = assets[spec.asset_keys[0]];
  if (!first) throw Error('Unregistered matrix image');
  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 550,
          top: 285,
          width: 820,
          height: 470,
          padding: 13,
          background: '#fff0df',
          transform: `rotate(${-4 + progress * 4}deg) scale(${1 - progress * 0.15})`,
          opacity: 1 - smooth(progress * 2.4),
          boxShadow: '0 25px 90px #0008',
        }}
      >
        <Img
          src={staticFile(first)}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      </div>
      {Array.from({ length: state.visible }, (_, i) => {
        const src = assets[spec.asset_keys[i % spec.asset_keys.length]];
        if (!src) throw Error('Unregistered matrix image');
        const t = smooth((progress - (i / spec.count) * 0.72) / 0.28),
          x = (i % columns) * tileW + 90,
          y = Math.floor(i / columns) * tileH + 275;
        return (
          <div
            key={i}
            data-matrix-tile={i}
            style={{
              position: 'absolute',
              left: 960 + (x - 960) * t,
              top: 510 + (y - 510) * t,
              width: tileW - 6,
              height: tileH - 6,
              opacity: 0.45 + 0.55 * t,
              transform: `scale(${0.3 + 0.7 * t})`,
              border: '1px solid #e7c8e077',
              boxShadow: '0 2px 10px #0005',
              overflow: 'hidden',
            }}
          >
            <Img
              src={staticFile(src)}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                objectPosition: `${20 + (i % 5) * 15}% 50%`,
              }}
            />
          </div>
        );
      })}
      <div
        style={{
          position: 'absolute',
          right: 100,
          bottom: 125,
          textAlign: 'right',
          color: '#fff1ce',
        }}
      >
        <span style={{ fontSize: 78, fontVariantNumeric: 'tabular-nums', fontWeight: 700 }}>
          {state.visible.toLocaleString('en-US')}
        </span>
        <span style={{ fontSize: 26, marginLeft: 18 }}>格画面 · 排列与计数同步</span>
      </div>
    </>
  );
}
function Network({
  entity,
  progress,
  effect,
}: {
  entity: SemanticEntity;
  progress: number;
  effect: number;
}) {
  const spec = entity.spatial!,
    { nodes, edges } = networkGeometry(spec, progress),
    wave = propagationState(spec, effect);
  const px = (i: number) => 100 + nodes[i].x * 1720,
    py = (i: number) => 225 + nodes[i].y * 620;
  return (
    <>
      <svg
        viewBox="0 0 1920 1080"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        <defs>
          <filter id={`glow-${entity.id}`}>
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>
        {edges.map((e) => (
          <line
            key={e.id}
            data-network-edge={e.id}
            x1={px(e.from)}
            y1={py(e.from)}
            x2={px(e.to)}
            y2={py(e.to)}
            stroke={wave.reached[e.from] && wave.reached[e.to] ? '#ffb48f' : '#8cbbcd'}
            strokeWidth={wave.reached[e.from] && wave.reached[e.to] ? 2.7 : 1.1}
            opacity={wave.reached[e.from] && wave.reached[e.to] ? 0.85 : 0.26}
          />
        ))}
        {nodes.map((n, i) => (
          <g key={n.id} data-network-node={n.id}>
            {wave.reached[i] && (
              <circle
                cx={px(i)}
                cy={py(i)}
                r="19"
                fill="#ffb48f"
                opacity="0.3"
                filter={`url(#glow-${entity.id})`}
              />
            )}
            <circle
              cx={px(i)}
              cy={py(i)}
              r={i === spec.source_node ? 12 : 7}
              fill={wave.reached[i] ? '#ffd5a3' : '#93dce4'}
              stroke="#fff0d0"
              strokeWidth="1"
            />
            {i % 8 === 0 && (
              <text x={px(i) + 20} y={py(i) + 5} fill="#e1e8e9" fontSize="20">
                {String(i + 1).padStart(2, '0')}
              </text>
            )}
          </g>
        ))}
      </svg>
      <div style={{ position: 'absolute', left: 100, bottom: 135, fontSize: 26, color: '#b4c9d4' }}>
        {spec.count} 个节点 · 身份和连接保持一致
      </div>
      {effect > 0 && (
        <div
          style={{ position: 'absolute', right: 100, bottom: 130, fontSize: 31, color: '#ffd5a3' }}
        >
          影响已传递至 <b style={{ fontSize: 56 }}>{wave.count}</b> 个节点
        </div>
      )}
    </>
  );
}
export default function SpatialPanel({
  scene,
  entity,
  frame,
  width,
  height,
  assets,
}: {
  scene: Scene;
  entity: SemanticEntity;
  frame: number;
  width: number;
  height: number;
  assets: Record<string, string>;
}) {
  const theme = useTheme(),
    spec = entity.spatial!;
  const progress = normalized(scene, entity.parameter_id!, frame);
  const effect = spec.effect_parameter_id ? normalized(scene, spec.effect_parameter_id, frame) : 0;
  const scale = Math.min(width / 1920, height / 1080);
  return (
    <div
      data-spatial-component={entity.component}
      data-spatial-progress={progress.toFixed(4)}
      style={{ position: 'relative', width, height, overflow: 'hidden', color: theme.ink }}
    >
      <div
        style={{
          position: 'absolute',
          left: (width - 1920 * scale) / 2,
          top: (height - 1080 * scale) / 2,
          width: 1920,
          height: 1080,
          transform: `scale(${scale})`,
          transformOrigin: '0 0',
        }}
      >
        <Atmosphere frame={frame} />
        {entity.component === 'SpatialCity' ? (
          <City spec={spec} progress={progress} frame={frame} width={1920} height={1080} />
        ) : entity.component === 'QuantityMatrix' ? (
          <Matrix scene={scene} entity={entity} frame={frame} progress={progress} assets={assets} />
        ) : (
          <Network entity={entity} progress={progress} effect={effect} />
        )}
        <div
          style={{ position: 'absolute', left: 100, top: 85, right: 100, pointerEvents: 'none' }}
        >
          <div style={{ fontSize: 18, letterSpacing: 5, color: '#b4dce4', marginBottom: 18 }}>
            MAKE THE INVISIBLE VISIBLE
          </div>
          <div
            style={{
              fontSize: 58,
              lineHeight: 1.2,
              fontWeight: 750,
              color: '#fff1d4',
              textShadow: '0 3px 25px #090d22',
            }}
          >
            {entity.title}
          </div>
          {entity.text && (
            <div style={{ fontSize: 26, color: '#c9cbdd', marginTop: 22 }}>{entity.text}</div>
          )}
        </div>
      </div>
    </div>
  );
}
