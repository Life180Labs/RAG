export type MessageRole = 'user' | 'assistant';

export interface Conversation {
  id: string;
  repository_id: string;
  document_id: string;
  vector_index_id: string;
  prompt_template_id: string | null;
  title: string | null;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface CreateConversationRequest {
  title?: string | null;
  prompt_template_id?: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  token_count: number;
  retrieval_id: string | null;
  prompt_id: string | null;
  llm_request_id: string | null;
  created_at: string;
}

export interface SendMessageRequest {
  content: string;
}

export interface MessageTurn {
  user_message: Message;
  assistant_message: Message;
}

export interface ConversationMemory {
  id: string;
  user_id: string;
  repository_id: string;
  custom_instructions: string | null;
  preferences: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateConversationMemoryRequest {
  custom_instructions?: string | null;
  preferences?: Record<string, unknown> | null;
}
