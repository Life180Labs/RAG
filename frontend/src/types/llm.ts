export type RoutingHint = 'fast' | 'reasoning' | 'large_context' | 'low_budget' | 'offline';

export const ROUTING_HINTS: { value: RoutingHint; label: string }[] = [
  { value: 'fast', label: 'Fast' },
  { value: 'reasoning', label: 'Reasoning' },
  { value: 'large_context', label: 'Large context' },
  { value: 'low_budget', label: 'Low budget' },
  { value: 'offline', label: 'Offline (local)' },
];

export interface ModelSpec {
  provider: string;
  model: string;
  context_window: number;
  price_per_1m_input: number;
  price_per_1m_output: number;
  supports_streaming: boolean;
  supports_json_mode: boolean;
  supports_vision: boolean;
  supports_function_calling: boolean;
  supports_reasoning: boolean;
  is_fast: boolean;
  is_reasoning: boolean;
}

export interface ProviderHealth {
  provider: string;
  configured: boolean;
  healthy: boolean;
}

export type LLMRequestStatus = 'pending' | 'completed' | 'failed';

export interface AttemptRecord {
  provider: string;
  model: string;
  error: string | null;
}

export interface LLMRequest {
  id: string;
  prompt_id: string;
  provider: string;
  model: string;
  routing_hint: string | null;
  input_text: string;
  output_text: string | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number | null;
  latency_ms: number | null;
  stream: boolean;
  json_mode: boolean;
  attempted_providers: AttemptRecord[] | null;
  status: LLMRequestStatus;
  status_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCompletionRequest {
  provider?: string | null;
  model?: string | null;
  routing_hint?: RoutingHint | null;
  json_mode?: boolean;
}
