import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as llmService from '@/services/llm-service';
import type { CreateCompletionRequest } from '@/types/llm';

export function useModels() {
  return useQuery({
    queryKey: ['llm', 'models'],
    queryFn: ({ signal }) => llmService.listModels(signal),
    select: (response) => response.data,
    staleTime: Infinity,
  });
}

export function useProviderHealth(provider: string | null) {
  return useQuery({
    queryKey: ['llm', 'models', provider, 'health'],
    queryFn: ({ signal }) => llmService.getProviderHealth(provider as string, signal),
    select: (response) => response.data,
    enabled: Boolean(provider),
  });
}

export function useCompletions(
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  promptId: string | null,
) {
  return useQuery({
    queryKey: [
      'documents',
      documentId,
      'vector-indexes',
      vectorIndexId,
      'retrievals',
      retrievalId,
      'prompts',
      promptId,
      'completions',
    ],
    queryFn: ({ signal }) =>
      llmService.listCompletions(
        documentId,
        vectorIndexId,
        retrievalId,
        promptId as string,
        signal,
      ),
    select: (response) => response.data,
    enabled:
      Boolean(documentId) && Boolean(vectorIndexId) && Boolean(retrievalId) && Boolean(promptId),
  });
}

export function useCreateCompletion(
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  promptId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCompletionRequest) =>
      llmService.createCompletion(documentId, vectorIndexId, retrievalId, promptId, payload),
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
          promptId,
          'completions',
        ],
      }),
  });
}
