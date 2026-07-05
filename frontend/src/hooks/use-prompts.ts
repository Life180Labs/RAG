import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as promptService from '@/services/prompt-service';
import type { CreatePromptRequest, CreatePromptTemplateRequest } from '@/types/prompt';

export function usePromptTemplates(repositoryId: string | null) {
  return useQuery({
    queryKey: ['repositories', repositoryId, 'prompt-templates'],
    queryFn: ({ signal }) => promptService.listPromptTemplates(repositoryId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(repositoryId),
  });
}

export function useCreatePromptTemplate(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreatePromptTemplateRequest) =>
      promptService.createPromptTemplate(repositoryId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['repositories', repositoryId, 'prompt-templates'],
      }),
  });
}

export function usePromptTemplateVersions(repositoryId: string | null, name: string | null) {
  return useQuery({
    queryKey: ['repositories', repositoryId, 'prompt-templates', name, 'versions'],
    queryFn: ({ signal }) =>
      promptService.listPromptTemplateVersions(repositoryId as string, name as string, signal),
    select: (response) => response.data,
    enabled: Boolean(repositoryId) && Boolean(name),
  });
}

export function useArchivePromptTemplate(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      promptService.archivePromptTemplate(repositoryId, templateId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['repositories', repositoryId, 'prompt-templates'],
      }),
  });
}

export function usePrompts(documentId: string, vectorIndexId: string, retrievalId: string | null) {
  return useQuery({
    queryKey: [
      'documents',
      documentId,
      'vector-indexes',
      vectorIndexId,
      'retrievals',
      retrievalId,
      'prompts',
    ],
    queryFn: ({ signal }) =>
      promptService.listPrompts(documentId, vectorIndexId, retrievalId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(vectorIndexId) && Boolean(retrievalId),
  });
}

export function useBuildPrompt(documentId: string, vectorIndexId: string, retrievalId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreatePromptRequest) =>
      promptService.buildPrompt(documentId, vectorIndexId, retrievalId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: [
          'documents',
          documentId,
          'vector-indexes',
          vectorIndexId,
          'retrievals',
          retrievalId,
          'prompts',
        ],
      }),
  });
}
