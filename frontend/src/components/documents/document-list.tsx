'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ChunkExplorer } from '@/components/chunks/chunk-explorer';
import { useDeleteDocument, useDocuments, useRestoreDocument } from '@/hooks/use-documents';
import { ApiRequestError } from '@/services/api-client';
import { downloadDocument } from '@/services/document-service';
import type { Document, DocumentStatus } from '@/types/document';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

function statusVariant(status: DocumentStatus): 'default' | 'secondary' | 'destructive' {
  if (status.startsWith('failed')) return 'destructive';
  if (status === 'ready' || status === 'validated') return 'default';
  return 'secondary';
}

function statusLabel(status: DocumentStatus): string {
  return status.replace(/_/g, ' ');
}

export function DocumentList({ repositoryId }: { repositoryId: string }) {
  const { data: documents, isLoading, isError } = useDocuments(repositoryId);
  const deleteDocument = useDeleteDocument(repositoryId);
  const restoreDocument = useRestoreDocument(repositoryId);
  const [error, setError] = useState<string | null>(null);
  const [lastDeletedId, setLastDeletedId] = useState<string | null>(null);
  const [expandedChunksId, setExpandedChunksId] = useState<string | null>(null);

  async function handleDownload(doc: Document) {
    setError(null);
    try {
      await downloadDocument(doc.id, doc.filename);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to download this file.');
    }
  }

  async function handleDelete(documentId: string) {
    setError(null);
    try {
      await deleteDocument.mutateAsync(documentId);
      setLastDeletedId(documentId);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to delete this document.');
    }
  }

  async function handleRestore(documentId: string) {
    setError(null);
    try {
      await restoreDocument.mutateAsync(documentId);
      setLastDeletedId(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to restore this document.');
    }
  }

  if (isLoading) {
    return <Skeleton className="h-24 w-full" data-testid="document-list-loading" />;
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Couldn&apos;t load documents</AlertTitle>
      </Alert>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {lastDeletedId && (
        <Alert data-testid="document-deleted-notice">
          <AlertTitle>Document deleted</AlertTitle>
          <AlertDescription>
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0"
              onClick={() => handleRestore(lastDeletedId)}
            >
              Undo
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {documents && documents.length === 0 && (
        <p className="text-muted-foreground text-sm" data-testid="document-list-empty">
          No documents uploaded yet.
        </p>
      )}

      {documents && documents.length > 0 && (
        <ul className="divide-border divide-y text-sm" data-testid="document-list">
          {documents.map((doc) => (
            <li key={doc.id} className="space-y-2 py-2">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{doc.filename}</p>
                  <p className="text-muted-foreground text-xs">
                    {formatBytes(doc.size_bytes)} · v{doc.current_version} ·{' '}
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                  {doc.status_message && (
                    <p className="text-destructive text-xs">{doc.status_message}</p>
                  )}
                </div>
                <Badge variant={statusVariant(doc.status)}>{statusLabel(doc.status)}</Badge>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => handleDownload(doc)}>
                    Download
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedChunksId(expandedChunksId === doc.id ? null : doc.id)}
                  >
                    Chunks
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(doc.id)}
                    disabled={deleteDocument.isPending}
                  >
                    Delete
                  </Button>
                </div>
              </div>

              {expandedChunksId === doc.id && <ChunkExplorer documentId={doc.id} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
