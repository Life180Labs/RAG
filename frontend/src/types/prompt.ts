export type PromptStatus = 'pending' | 'completed' | 'failed';

export interface PromptTemplate {
  id: string;
  repository_id: string;
  name: string;
  version: number;
  system_prompt: string;
  formatting_instructions: string | null;
  output_schema: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePromptTemplateRequest {
  name: string;
  system_prompt: string;
  formatting_instructions?: string | null;
  output_schema?: Record<string, unknown> | null;
}

export interface Citation {
  source_label: string;
  document_id: string;
  document_filename: string;
  page: number | null;
  section: string | null;
  chunk_id: string;
  confidence: number;
}

export interface Prompt {
  id: string;
  retrieval_id: string;
  prompt_template_id: string | null;
  model_context_window: number;
  system_prompt_tokens: number;
  conversation_tokens: number;
  context_tokens: number;
  query_tokens: number;
  response_budget_tokens: number;
  total_tokens: number;
  rendered_system_prompt: string | null;
  rendered_context: string | null;
  rendered_prompt: string | null;
  citations: Citation[] | null;
  status: PromptStatus;
  status_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreatePromptRequest {
  prompt_template_id?: string | null;
  system_prompt?: string | null;
  formatting_instructions?: string | null;
  output_schema?: Record<string, unknown> | null;
  model_context_window?: number;
  response_reserve_tokens?: number;
  order_by_page?: boolean;
}
