import { tokenStorage } from '@/lib/token-storage';
import { apiDelete, apiGet, apiPatch, apiPost, ApiRequestError } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type {
  Conversation,
  ConversationMemory,
  CreateConversationRequest,
  Message,
  MessageTurn,
  SendMessageRequest,
  UpdateConversationMemoryRequest,
} from '@/types/conversation';

const conversationsBasePath = (documentId: string, vectorIndexId: string) =>
  `/documents/${documentId}/vector-indexes/${vectorIndexId}/conversations`;

export const listConversations = (
  documentId: string,
  vectorIndexId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<Conversation[]>>(
    conversationsBasePath(documentId, vectorIndexId),
    signal,
  );

export const createConversation = (
  documentId: string,
  vectorIndexId: string,
  payload: CreateConversationRequest,
) =>
  apiPost<ApiSuccessResponse<Conversation>>(
    conversationsBasePath(documentId, vectorIndexId),
    payload,
  );

export const getConversation = (
  documentId: string,
  vectorIndexId: string,
  conversationId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<Conversation>>(
    `${conversationsBasePath(documentId, vectorIndexId)}/${conversationId}`,
    signal,
  );

export const deleteConversation = (
  documentId: string,
  vectorIndexId: string,
  conversationId: string,
) =>
  apiDelete<ApiSuccessResponse<{ deleted: boolean }>>(
    `${conversationsBasePath(documentId, vectorIndexId)}/${conversationId}`,
  );

export const listMessages = (
  documentId: string,
  vectorIndexId: string,
  conversationId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<Message[]>>(
    `${conversationsBasePath(documentId, vectorIndexId)}/${conversationId}/messages`,
    signal,
  );

export const sendMessage = (
  documentId: string,
  vectorIndexId: string,
  conversationId: string,
  payload: SendMessageRequest,
) =>
  apiPost<ApiSuccessResponse<MessageTurn>>(
    `${conversationsBasePath(documentId, vectorIndexId)}/${conversationId}/messages`,
    payload,
  );

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

// The export endpoint returns raw text/markdown, not the JSON envelope
// apiRequest expects, so it fetches directly rather than going through apiGet.
export async function exportConversationMarkdown(
  documentId: string,
  vectorIndexId: string,
  conversationId: string,
): Promise<string> {
  const accessToken = tokenStorage.getAccessToken();
  const response = await fetch(
    `${API_BASE_URL}${conversationsBasePath(documentId, vectorIndexId)}/${conversationId}/export`,
    { headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {} },
  );
  if (!response.ok) {
    throw new ApiRequestError(
      `Failed to export conversation (status ${response.status})`,
      response.status,
    );
  }
  return response.text();
}

export const getConversationMemory = (repositoryId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<ConversationMemory>>(
    `/repositories/${repositoryId}/conversation-memory`,
    signal,
  );

export const updateConversationMemory = (
  repositoryId: string,
  payload: UpdateConversationMemoryRequest,
) =>
  apiPatch<ApiSuccessResponse<ConversationMemory>>(
    `/repositories/${repositoryId}/conversation-memory`,
    payload,
  );
