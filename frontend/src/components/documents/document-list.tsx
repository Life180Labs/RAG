'use client';

import { useState } from 'react';
import { Download, Layers, Trash2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ChunkExplorer } from '@/components/chunks/chunk-explorer';
import { useDeleteDocument, useDocuments, useRestoreDocument } from '@/hooks/use-documents';
import { ApiRequestError } from '@/services/api-client';
import { downloadDocument } from '@/services/document-service';
import { cn } from '@/lib/utils';
import type { Document, DocumentStatus } from '@/types/document';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

function statusVariant(status: DocumentStatus): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status.startsWith('failed')) return 'destructive';
  if (status === 'ready') return 'default';
  if (status === 'validated') return 'secondary';
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
    return (
      <div className="space-y-2" data-testid="document-list-loading">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
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
              className="h-auto p-0 text-xs"
              onClick={() => handleRestore(lastDeletedId)}
            >
              Undo
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {documents && documents.length === 0 && (
        <p className="py-6 text-center text-sm text-muted-foreground" data-testid="document-list-empty">
          No documents uploaded yet.
        </p>
      )}

      {documents && documents.length > 0 && (
        <ul
          className="divide-y divide-border overflow-hidden rounded-lg border border-border"
          data-testid="document-list"
        >
          {documents.map((doc) => (
            <li key={doc.id}>
              <div
                className={cn(
                  'flex items-center gap-3 bg-card px-4 py-3 text-sm transition-colors hover:bg-muted/20',
                  expandedChunksId === doc.id && 'bg-muted/10',
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-foreground">{doc.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(doc.size_bytes)} · v{doc.current_version} ·{' '}
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                  {doc.status_message && (
                    <p className="mt-0.5 text-xs text-destructive">{doc.status_message}</p>
                  )}
                </div>

                <Badge variant={statusVariant(doc.status)} className="shrink-0">
                  {statusLabel(doc.status)}
                </Badge>

                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="Download"
                    onClick={() => handleDownload(doc)}
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="Pipeline"
                    className={expandedChunksId === doc.id ? 'bg-muted text-foreground' : ''}
                    onClick={() => setExpandedChunksId(expandedChunksId === doc.id ? null : doc.id)}
                  >
                    <Layers className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="Delete"
                    onClick={() => handleDelete(doc.id)}
                    disabled={deleteDocument.isPending}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {expandedChunksId === doc.id && (
                <div className="border-t border-border bg-background/50 p-4">
                  <ChunkExplorer documentId={doc.id} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
