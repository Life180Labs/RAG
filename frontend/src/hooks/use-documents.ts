import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as documentService from '@/services/document-service';

export function useDocuments(repositoryId: string) {
  return useQuery({
    queryKey: ['repositories', repositoryId, 'documents'],
    queryFn: ({ signal }) => documentService.listDocuments(repositoryId, signal),
    select: (response) => response.data,
    enabled: Boolean(repositoryId),
  });
}

export function useDocument(documentId: string | null) {
  return useQuery({
    queryKey: ['documents', documentId],
    queryFn: ({ signal }) => documentService.getDocument(documentId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId),
  });
}

export function useDocumentVersions(documentId: string | null) {
  return useQuery({
    queryKey: ['documents', documentId, 'versions'],
    queryFn: ({ signal }) => documentService.listDocumentVersions(documentId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId),
  });
}

export function useUploadDocument(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (percent: number) => void }) =>
      documentService.uploadDocument(repositoryId, file, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId, 'documents'] });
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId] });
    },
  });
}

export function useUploadDocumentVersion(repositoryId: string, documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (percent: number) => void }) =>
      documentService.uploadDocumentVersion(documentId, file, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId, 'documents'] });
      queryClient.invalidateQueries({ queryKey: ['documents', documentId, 'versions'] });
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId] });
    },
  });
}

export function useDeleteDocument(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentService.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId, 'documents'] });
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId] });
    },
  });
}

export function useRestoreDocument(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentService.restoreDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId, 'documents'] });
      queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId] });
    },
  });
}
