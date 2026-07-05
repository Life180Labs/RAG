import { apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { CreateCompletionRequest, LLMRequest, ModelSpec, ProviderHealth } from '@/types/llm';

export const listModels = (signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<ModelSpec[]>>('/llm/models', signal);

export const getProviderHealth = (provider: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<ProviderHealth>>(`/llm/models/${provider}/health`, signal);

const completionsBasePath = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  promptId: string,
) =>
  `/documents/${documentId}/vector-indexes/${vectorIndexId}/retrievals/${retrievalId}` +
  `/prompts/${promptId}/completions`;

export const listCompletions = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  promptId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<LLMRequest[]>>(
    completionsBasePath(documentId, vectorIndexId, retrievalId, promptId),
    signal,
  );

export const createCompletion = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  promptId: string,
  payload: CreateCompletionRequest,
) =>
  apiPost<ApiSuccessResponse<LLMRequest>>(
    completionsBasePath(documentId, vectorIndexId, retrievalId, promptId),
    payload,
  );
