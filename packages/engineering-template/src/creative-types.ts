/** Platform-owned free-subject creation and causal timing contract. */
export type CreativeElement = {
  id: string;
  role: 'subject' | 'environment' | 'prop' | 'annotation' | 'camera';
  description: string;
  implementation: 'source' | 'asset' | 'capture' | 'kit';
  library_ref?: string | null;
  source_file?: string | null;
  asset_key?: string | null;
};
export type CreativeEvent = {
  id: string;
  target: string;
  channel?: string;
  anchor: { phrase: string; occurrence?: number; edge?: 'start' | 'end'; offset_ms?: number };
  duration_ms: number;
  before: string;
  change: string;
  after: string;
  depends_on?: string[];
};
export type CompiledCreativeEvent = CreativeEvent & {
  start_frame: number;
  end_frame: number;
  timing_source: 'measured_words' | 'estimated_draft';
};
export type CreativeScene = {
  visual_goal: string;
  composition: string;
  palette: string[];
  techniques: ('svg' | 'canvas' | 'three' | 'images' | 'screen' | 'diagram')[];
  scene_source: string;
  elements: CreativeElement[];
  events: CreativeEvent[];
};
