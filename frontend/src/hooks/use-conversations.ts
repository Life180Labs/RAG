import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as conversationService from '@/services/conversation-service';
import type {
  CreateConversationRequest,
  SendMessageRequest,
  UpdateConversationMemoryRequest,
} from '@/types/conversation';

export function useConversations(documentId: string, vectorIndexId: string) {
  return useQuery({
    queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'conversations'],
    queryFn: ({ signal }) =>
      conversationService.listConversations(documentId, vectorIndexId, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(vectorIndexId),
  });
}

export function useCreateConversation(documentId: string, vectorIndexId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateConversationRequest) =>
      conversationService.createConversation(documentId, vectorIndexId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'conversations'],
      }),
  });
}

export function useDeleteConversation(documentId: string, vectorIndexId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) =>
      conversationService.deleteConversation(documentId, vectorIndexId, conversationId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'conversations'],
      }),
  });
}

export function useMessages(
  documentId: string,
  vectorIndexId: string,
  conversationId: string | null,
) {
  return useQuery({
    queryKey: [
      'documents',
      documentId,
      'vector-indexes',
      vectorIndexId,
      'conversations',
      conversationId,
      'messages',
    ],
    queryFn: ({ signal }) =>
      conversationService.listMessages(documentId, vectorIndexId, conversationId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(vectorIndexId) && Boolean(conversationId),
  });
}

export function useSendMessage(documentId: string, vectorIndexId: string, conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SendMessageRequest) =>
      conversationService.sendMessage(documentId, vectorIndexId, conversationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [
          'documents',
          documentId,
          'vector-indexes',
          vectorIndexId,
          'conversations',
          conversationId,
          'messages',
        ],
      });
      queryClient.invalidateQueries({
        queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'conversations'],
      });
    },
  });
}

export function useConversationMemory(repositoryId: string | null) {
  return useQuery({
    queryKey: ['repositories', repositoryId, 'conversation-memory'],
    queryFn: ({ signal }) =>
      conversationService.getConversationMemory(repositoryId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(repositoryId),
  });
}

export function useUpdateConversationMemory(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateConversationMemoryRequest) =>
      conversationService.updateConversationMemory(repositoryId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['repositories', repositoryId, 'conversation-memory'],
      }),
  });
}
