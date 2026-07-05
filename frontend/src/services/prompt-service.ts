import { apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type {
  CreatePromptRequest,
  CreatePromptTemplateRequest,
  Prompt,
  PromptTemplate,
} from '@/types/prompt';

const templatesBasePath = (repositoryId: string) =>
  `/repositories/${repositoryId}/prompt-templates`;

const promptsBasePath = (documentId: string, vectorIndexId: string, retrievalId: string) =>
  `/documents/${documentId}/vector-indexes/${vectorIndexId}/retrievals/${retrievalId}/prompts`;

export const listPromptTemplates = (repositoryId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<PromptTemplate[]>>(templatesBasePath(repositoryId), signal);

export const listPromptTemplateVersions = (
  repositoryId: string,
  name: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<PromptTemplate[]>>(
    `${templatesBasePath(repositoryId)}/${encodeURIComponent(name)}/versions`,
    signal,
  );

export const createPromptTemplate = (repositoryId: string, payload: CreatePromptTemplateRequest) =>
  apiPost<ApiSuccessResponse<PromptTemplate>>(templatesBasePath(repositoryId), payload);

export const archivePromptTemplate = (repositoryId: string, templateId: string) =>
  apiPost<ApiSuccessResponse<PromptTemplate>>(
    `${templatesBasePath(repositoryId)}/${templateId}/archive`,
  );

export const listPrompts = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<Prompt[]>>(
    promptsBasePath(documentId, vectorIndexId, retrievalId),
    signal,
  );

export const buildPrompt = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  payload: CreatePromptRequest,
) =>
  apiPost<ApiSuccessResponse<Prompt>>(
    promptsBasePath(documentId, vectorIndexId, retrievalId),
    payload,
  );
