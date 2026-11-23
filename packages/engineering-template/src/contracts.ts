import type { SemanticScene, CompiledSemanticEvent } from './semantic-types';
import type { CreativeScene, CompiledCreativeEvent } from './creative-types';
export type SceneObjectKind =
  | 'tv'
  | 'monitor'
  | 'laptop'
  | 'console'
  | 'player'
  | 'soundbar'
  | 'speaker'
  | 'remote'
  | 'phone'
  | 'server'
  | 'router';
export type ObjectAction =
  | 'reveal'
  | 'connect'
  | 'signal'
  | 'power_on'
  | 'power_off'
  | 'play'
  | 'sound'
  | 'press'
  | 'volume'
  | 'highlight';
export type ObjectEvent = {
  id: string;
  target: string;
  action: ObjectAction;
  anchor: { phrase: string; occurrence: number; edge: 'start' | 'end'; offset_ms: number };
  duration_ms: number;
  channel: 'video' | 'audio' | 'control' | 'data';
  reverse: boolean;
  value: number;
  depends_on: string[];
  sound: 'connect' | 'click' | 'notify' | null;
};
export type VisualScene = {
  schema_version: '1.0';
  purpose: string;
  setting: 'studio' | 'living_room' | 'desktop';
  objects: {
    id: string;
    kind: SceneObjectKind;
    label: string;
    x: number;
    y: number;
    width: number;
    height: number;
    color: string;
    powered: boolean;
    screen: 'landscape' | 'game' | 'stream' | 'pixels' | 'black';
    playback: 'smooth' | 'stepped';
    hdr: boolean;
    ports: {
      id: string;
      side: 'left' | 'right' | 'top' | 'bottom';
      kind: 'hdmi' | 'network' | 'wireless' | 'generic';
      position: number;
      label: string;
    }[];
  }[];
  connections: {
    id: string;
    source: string;
    source_port: string;
    target: string;
    target_port: string;
    label: string;
    kind: 'cable' | 'wireless';
    connected: boolean;
  }[];
  events: ObjectEvent[];
  sound_enabled: boolean;
  sound_volume: number;
};
export type CompiledObjectEvent = Omit<ObjectEvent, 'anchor' | 'duration_ms' | 'depends_on'> & {
  start_frame: number;
  end_frame: number;
  timing_source: 'measured_words' | 'estimated_draft';
};
export type ContentIntent =
  | 'introduction'
  | 'explanation'
  | 'analysis'
  | 'viewpoint'
  | 'advice'
  | 'tutorial';
export type EditorialRequest = {
  intent: ContentIntent | 'auto';
  secondary_intents: ContentIntent[];
  subject_kind:
    | 'auto'
    | 'project'
    | 'product'
    | 'technology'
    | 'knowledge'
    | 'concept'
    | 'mechanism'
    | 'method'
    | 'workflow'
    | 'problem'
    | 'phenomenon';
  audience_description: string;
  audience_level: 'auto' | 'introductory' | 'intermediate' | 'advanced';
  presentation_forms: string[];
  core_message: string;
  viewer_takeaway: string;
};
export type ContentStrategy = {
  taxonomy_version: '1.0';
  intent: ContentIntent;
  secondary_intents: ContentIntent[];
  subject_kind: Exclude<EditorialRequest['subject_kind'], 'auto'>;
  audience_description: string;
  audience_level: Exclude<EditorialRequest['audience_level'], 'auto'>;
  presentation_forms: string[];
  rationale: string;
  success_criteria: string[];
  outline: { function: string; purpose: string; scene_ids: string[] }[];
};
export type Diagram = {
  nodes: {
    id: string;
    label: string;
    detail: string;
    x: number;
    y: number;
    reveal: number;
    emphasis: 'none' | 'pulse';
  }[];
  edges: { source: string; target: string; label: string; reveal: number }[];
};
export type Scene = {
  id: string;
  role?:
    | 'content'
    | 'opening'
    | 'hook'
    | 'problem'
    | 'argument'
    | 'example'
    | 'mechanism'
    | 'demonstration'
    | 'limitation'
    | 'recommendation'
    | 'closing';
  message?: string;
  viewer_question?: string;
  disclosures?: { text: string; start_seconds: number; end_seconds: number }[];
  type: 'title' | 'cards' | 'flow' | 'architecture' | 'code' | 'terminal' | 'ui' | 'summary';
  title: string;
  subtitle: string;
  narration: string;
  bullets: string[];
  code: string;
  claim_ids: string[];
  evidence_ids: string[];
  verification: 'concept' | 'static' | 'runtime' | 'user_provided';
  duration: number;
  start_frame: number;
  frames: number;
  audio_id?: string | null;
  media_id?: string | null;
  audio_src?: string;
  media_src?: string;
  media_kind: 'image' | 'video';
  locked: boolean;
  motion?: {
    schema_version: '4.0';
    purpose: string;
    layout?: 'grid' | 'fan';
    code_focus?: { element_id: string; line: number; end_line?: number | null }[];
    chapter: string;
    pattern: 'overview' | 'code_scan' | 'compare' | 'graph' | 'capacity' | 'queue' | 'depth';
    elements: { id: string; label: string }[];
    events: {
      id: string;
      target: string;
      action: 'reveal' | 'highlight' | 'progress';
      anchor: { phrase: string; occurrence: number; edge: 'start' | 'end'; offset_ms: number };
      duration_ms: number;
    }[];
  } | null;
  compiled_events?: {
    id: string;
    target: string;
    action: 'reveal' | 'highlight' | 'progress';
    start_frame: number;
    end_frame: number;
    timing_source: string;
  }[];
  semantic_scene?: SemanticScene | null;
  compiled_semantic_events?: CompiledSemanticEvent[];
  creation?: CreativeScene | null;
  compiled_creative_events?: CompiledCreativeEvent[];
  visual_scene?: VisualScene | null;
  compiled_object_events?: CompiledObjectEvent[];
  diagram?: Diagram | null;
  cues: { start: number; end: number; text: string }[];
};
export type Storyboard = {
  schema_version: '1.0';
  title: string;
  language: 'zh-CN' | 'en-US';
  accent: 'blue' | 'violet' | 'teal' | 'amber';
  audience: string;
  editorial_request?: EditorialRequest;
  presentation_profile?: 'creator' | 'internal_demo' | 'engineering_report';
  creator_brand?: string;
  cover?: { headline: string; subtitle: string } | null;
  editorial?: {
    strategy?: ContentStrategy | null;
    audience_question: string;
    core_message: string;
    viewer_takeaway: string;
    hook: string;
    closing: string;
    supports: { message: string; claim_ids: string[]; evidence_ids: string[] }[];
    cover: { headline: string; subtitle: string };
  } | null;
  scenes: Scene[];
  fps: 30;
  width: 1920 | 3840;
  height: 1080 | 2160;
  design_pack?: 'editorial_warm' | 'workspace_tech' | 'neon_horizon';
  motion_review_required?: boolean;
  total_frames: number;
  notices: string[];
  audio_alignment: 'estimated_sentence' | 'native_words' | 'forced_words' | 'mixed' | 'none';
};
export type VideoProps = Storyboard & {
  generated_assets?: Record<string, string>;
  fontSrc?: string;
  assetBase?: string;
  preview?: boolean;
};
