// Platform-owned, bounded causal coverage. Never discard a late semantic event.
export function reviewWindows(scene, fps) {
  const events = scene.compiled_semantic_events || [];
  if (!events.length) {
    const event =
      scene.compiled_object_events?.find((e) => ['play', 'sound', 'signal'].includes(e.action)) ||
      scene.compiled_events?.[0];
    const start = scene.start_frame + Math.max(0, (event?.start_frame || 0) - Math.round(fps / 2));
    return [{ start, end: Math.min(scene.start_frame + scene.frames - 1, start + fps * 4 - 1) }];
  }
  const windows = [];
  for (const e of events) {
    const start = scene.start_frame + Math.max(0, e.start_frame - 8),
      end = scene.start_frame + Math.min(scene.frames - 1, e.end_frame + 12);
    const last = windows.at(-1);
    if (last && start <= last.end && end - last.start < fps * 5) {
      last.end = Math.max(last.end, end);
    } else windows.push({ start, end });
  }
  return windows;
}
export function causalFrames(scene) {
  return (scene.compiled_semantic_events || [])
    .flatMap((e) => [
      Math.max(0, e.start_frame - 1),
      Math.floor((e.start_frame + e.end_frame) / 2),
      Math.min(scene.frames - 1, e.end_frame + 1),
    ])
    .map((f) => scene.start_frame + f);
}
