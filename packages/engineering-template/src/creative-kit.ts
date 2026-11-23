/** Pure, protected timing helpers for authored SVG/Canvas/Three scenes. No subject templates. */
import type { CompiledCreativeEvent } from './creative-types';

export function creativeProgress(
  scene: { compiled_creative_events?: CompiledCreativeEvent[] },
  eventId: string,
  frame: number,
  easing: 'linear' | 'smooth' = 'smooth',
) {
  const event = scene.compiled_creative_events?.find((e) => e.id === eventId);
  if (!event || event.end_frame <= event.start_frame)
    throw Error('Missing compiled creative event: ' + eventId);
  const p = Math.max(
    0,
    Math.min(1, (frame - event.start_frame) / (event.end_frame - event.start_frame)),
  );
  return easing === 'smooth' ? p * p * (3 - 2 * p) : p;
}

export function registeredMaterial(assets: Record<string, string> | undefined, key: string) {
  const file = assets?.[key];
  if (!file) throw Error('Missing registered material: ' + key);
  return file;
}
