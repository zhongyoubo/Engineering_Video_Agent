/** Protected renderer for validated embedded GLB receipts. No arbitrary/network model URLs. */
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { cancelRender, continueRender, delayRender, staticFile, useVideoConfig } from 'remotion';
import { ThreeCanvas } from '@remotion/three';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

function disposeModel(object: THREE.Group) {
  const geometries = new Set<THREE.BufferGeometry>(),
    materials = new Set<THREE.Material>(),
    textures = new Set<THREE.Texture>();
  object.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (mesh.geometry) geometries.add(mesh.geometry);
    const list = mesh.material
      ? Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]
      : [];
    for (const material of list) {
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  textures.forEach((texture) => texture.dispose());
}

function Model({ file, angle }: { file: string; angle: number }) {
  const { gl, scene, camera } = useThree();
  const loadingHold = useRef<number | null>(null);
  const [object, setObject] = useState<THREE.Group | null>(null);
  // Allocate only on commit and release on unmount, including interrupted async loads.
  // Render-time allocation can leak a hold when React discards a render or replays effects.
  useLayoutEffect(() => {
    const handle = delayRender('Embedded library GLB');
    loadingHold.current = handle;
    return () => {
      continueRender(handle);
      if (loadingHold.current === handle) loadingHold.current = null;
    };
  }, [file]);
  useEffect(() => {
    let active = true;
    let loaded: THREE.Group | null = null;
    new GLTFLoader().load(
      staticFile(file),
      (gltf) => {
        if (!active) {
          disposeModel(gltf.scene);
          return;
        }
        const root = gltf.scene;
        loaded = root;
        const box = new THREE.Box3().setFromObject(root);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const scale = 2.6 / Math.max(size.x, size.y, size.z, 0.0001);
        root.position.copy(center).multiplyScalar(-scale);
        root.scale.setScalar(scale);
        setObject(root);
      },
      undefined,
      (error) => {
        if (active)
          cancelRender(error instanceof Error ? error : new Error('Library GLB load failed'));
      },
    );
    return () => {
      active = false;
      if (loaded) disposeModel(loaded);
    };
  }, [file]);
  useLayoutEffect(() => {
    if (object) {
      // Loading can finish AFTER ThreeCanvas's frame effect. Render the committed primitive
      // before releasing its hold; a successful loader alone would allow blank stills.
      const hold = delayRender('Commit and draw embedded model pose');
      const task = requestAnimationFrame(() => {
        try {
          scene.updateMatrixWorld(true);
          camera.updateMatrixWorld();
          gl.render(scene, camera);
        } catch (error) {
          cancelRender(error instanceof Error ? error : new Error('Library GLB draw failed'));
        } finally {
          if (loadingHold.current !== null) {
            continueRender(loadingHold.current);
            loadingHold.current = null;
          }
          continueRender(hold);
        }
      });
      return () => {
        cancelAnimationFrame(task);
        continueRender(hold);
      };
    }
  }, [object, angle, gl, scene, camera]);
  return object ? (
    <group rotation={[0, angle, 0]}>
      <primitive object={object} />
    </group>
  ) : null;
}

/** angle is a frame-derived value in radians; an image receipt is intentionally rejected. */
export function LibraryModel({
  asset,
  angle = 0,
  width,
  height,
}: {
  asset: string;
  angle?: number;
  width: number;
  height: number;
}) {
  const output = useVideoConfig();
  if (typeof asset !== 'string' || !/^generated\/[a-f0-9]{64}\.glb$/.test(asset))
    throw Error('LibraryModel requires a validated local GLB receipt');
  if (
    !Number.isFinite(angle) ||
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    width <= 0 ||
    height <= 0
  )
    throw Error('LibraryModel requires finite dimensions and frame pose');
  const camera = useMemo(() => ({ position: [0, 0, 5] as [number, number, number], fov: 38 }), []);
  return (
    <ThreeCanvas
      width={width}
      height={height}
      dpr={Math.max(1, output.width / 1920)}
      camera={camera}
      gl={{ alpha: true, antialias: true, preserveDrawingBuffer: true }}
    >
      <ambientLight intensity={1.5} />
      <directionalLight position={[4, 5, 5]} intensity={3} />
      <directionalLight position={[-3, 1, -2]} intensity={1.4} color="#9acadd" />
      <Model key={asset} file={asset} angle={angle} />
    </ThreeCanvas>
  );
}
