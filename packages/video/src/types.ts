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
  diagram?: Diagram | null;
  cues: { start: number; end: number; text: string }[];
};
export type Storyboard = {
  schema_version: '1.0';
  title: string;
  language: 'zh-CN' | 'en-US';
  accent: 'blue' | 'violet' | 'teal' | 'amber';
  audience: string;
  presentation_profile?: 'creator' | 'internal_demo' | 'engineering_report';
  creator_brand?: string;
  cover?: { headline: string; subtitle: string } | null;
  editorial?: {
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
  design_pack?: 'editorial_warm' | 'workspace_tech';
  motion_review_required?: boolean;
  total_frames: number;
  notices: string[];
  audio_alignment: 'estimated_sentence' | 'native_words' | 'forced_words' | 'mixed' | 'none';
};
export type VideoProps = Storyboard & { fontSrc?: string; assetBase?: string; preview?: boolean };
