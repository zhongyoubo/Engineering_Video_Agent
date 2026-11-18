export type SemanticComponent =
  | 'PromptInput'
  | 'Conversation'
  | 'TokenSequence'
  | 'ContextWindow'
  | 'DocumentChunks'
  | 'RetrievalResults'
  | 'ModelBoundary'
  | 'ToolCall'
  | 'TaskState'
  | 'EvidenceStack'
  | 'ApprovalGate'
  | 'CodeWorkspace'
  | 'AssetImage';
export type SemanticState =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'awaiting_confirmation'
  | 'rejected'
  | 'cancelled';
export type SemanticItem = { text: string; detail: string; active: boolean };
export type SemanticEntity = {
  id: string;
  component: SemanticComponent;
  title: string;
  text: string;
  items: SemanticItem[];
  state: SemanticState;
  x: number;
  y: number;
  width: number;
  height: number;
  bind_to?: string | null;
  asset_key?: string | null;
  provenance: 'illustrative' | 'observed';
  evidence_ids: string[];
};
export type SemanticEvent = {
  id: string;
  target: string;
  action: 'transition' | 'replace' | 'append' | 'select' | 'highlight';
  anchor: { phrase: string; occurrence: number; edge: 'start' | 'end'; offset_ms: number };
  duration_ms: number;
  depends_on: string[];
  from_state?: SemanticState | null;
  to_state?: SemanticState | null;
  text?: string | null;
  items: SemanticItem[];
  selected?: number | null;
};
export type CompiledSemanticEvent = SemanticEvent & {
  start_frame: number;
  end_frame: number;
  timing_source: 'measured_words' | 'estimated_draft';
};
export type SemanticScene = {
  schema_version: '1.0';
  viewer_question: string;
  entities: SemanticEntity[];
  events: SemanticEvent[];
  expectations: { id: string; event_id: string; visible_result: string }[];
};
