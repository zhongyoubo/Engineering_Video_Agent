// Platform-owned rendering capability selection. No subject keywords or source evaluation.
export function requiresWebGL(props) {
  return props.scenes.some(
    (scene) =>
      scene.creation?.techniques?.includes('three') ||
      scene.semantic_scene?.entities?.some((entity) => entity.component === 'SpatialCity'),
  );
}
