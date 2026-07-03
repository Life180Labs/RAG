import { apiDelete, apiDownload, apiGet, apiPost, apiUpload } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { Document, DocumentVersion } from '@/types/document';

export const listDocuments = (repositoryId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Document[]>>(`/repositories/${repositoryId}/documents`, signal);

export const listDocumentVersions = (documentId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<DocumentVersion[]>>(`/documents/${documentId}/versions`, signal);

export const uploadDocument = (
  repositoryId: string,
  file: File,
  onProgress?: (percent: number) => void,
) =>
  apiUpload<ApiSuccessResponse<Document>>(`/repositories/${repositoryId}/documents`, file, {
    onProgress,
  });

export const uploadDocumentVersion = (
  documentId: string,
  file: File,
  onProgress?: (percent: number) => void,
) =>
  apiUpload<ApiSuccessResponse<Document>>(`/documents/${documentId}/versions`, file, {
    onProgress,
  });

export const deleteDocument = (documentId: string) =>
  apiDelete<ApiSuccessResponse<{ deleted: boolean }>>(`/documents/${documentId}`);

export const restoreDocument = (documentId: string) =>
  apiPost<ApiSuccessResponse<Document>>(`/documents/${documentId}/restore`);

export async function downloadDocument(
  documentId: string,
  fallbackFilename: string,
): Promise<void> {
  const result = await apiDownload(`/documents/${documentId}/download`);

  if (result.kind === 'redirect') {
    window.open(result.url, '_blank', 'noopener,noreferrer');
    return;
  }

  const objectUrl = URL.createObjectURL(result.blob);
  const link = window.document.createElement('a');
  link.href = objectUrl;
  link.download = result.filename || fallbackFilename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
