'use client';

import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useCreateOrRebuildIndex,
  useDeleteVectorIndex,
  useVectorIndexes,
} from '@/hooks/use-vector-indexes';
import { ApiRequestError } from '@/services/api-client';
import {
  VECTOR_INDEX_PROVIDERS,
  VECTOR_INDEX_TYPES,
  type VectorIndexProviderName,
  type VectorIndexStatus,
  type VectorIndexType,
} from '@/types/vector-index';

function statusVariant(status: VectorIndexStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'failed') return 'destructive';
  if (status === 'ready') return 'default';
  return 'secondary';
}

export function VectorIndexExplorer({
  documentId,
  chunkSetId,
  embeddingVersionId,
}: {
  documentId: string;
  chunkSetId: string;
  embeddingVersionId: string;
}) {
  const [selectedProvider, setSelectedProvider] = useState<VectorIndexProviderName>('pgvector');
  const [selectedIndexType, setSelectedIndexType] = useState<VectorIndexType>('hnsw');
  const [error, setError] = useState<string | null>(null);

  const { data: indexes, isLoading } = useVectorIndexes(documentId, chunkSetId, embeddingVersionId);
  const createOrRebuild = useCreateOrRebuildIndex(documentId, chunkSetId, embeddingVersionId);
  const deleteIndex = useDeleteVectorIndex(documentId, chunkSetId, embeddingVersionId);

  async function handleCreate() {
    setError(null);
    try {
      await createOrRebuild.mutateAsync({
        provider: selectedProvider,
        indexType: selectedIndexType,
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create index.');
    }
  }

  async function handleDelete(vectorIndexId: string) {
    setError(null);
    try {
      await deleteIndex.mutateAsync(vectorIndexId);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to delete this index.');
    }
  }

  return (
    <div className="border-border space-y-2 border-t pt-2 pl-4" data-testid="vector-index-explorer">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <select
          className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
          value={selectedProvider}
          onChange={(event) => setSelectedProvider(event.target.value as VectorIndexProviderName)}
          data-testid="vector-index-provider-select"
        >
          {VECTOR_INDEX_PROVIDERS.map((provider) => (
            <option key={provider.value} value={provider.value}>
              {provider.label}
            </option>
          ))}
        </select>
        <select
          className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
          value={selectedIndexType}
          onChange={(event) => setSelectedIndexType(event.target.value as VectorIndexType)}
          data-testid="vector-index-type-select"
        >
          {VECTOR_INDEX_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={handleCreate} disabled={createOrRebuild.isPending}>
          {createOrRebuild.isPending ? 'Requesting…' : 'Create / rebuild index'}
        </Button>
      </div>

      {isLoading && <Skeleton className="h-8 w-full" data-testid="vector-indexes-loading" />}

      {indexes && indexes.length === 0 && (
        <p className="text-muted-foreground text-xs" data-testid="vector-indexes-empty">
          No indexes built yet.
        </p>
      )}

      {indexes && indexes.length > 0 && (
        <ul className="divide-border divide-y text-sm" data-testid="vector-indexes-list">
          {indexes.map((index) => (
            <li key={index.id} className="flex flex-wrap items-center justify-between gap-2 py-1">
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{index.provider}</span>
                <span className="text-muted-foreground text-xs">{index.index_type}</span>
                <span className="text-muted-foreground text-xs">
                  {index.vector_count} vectors
                  {index.build_duration_ms !== null ? ` · ${index.build_duration_ms}ms` : ''}
                </span>
                <Badge variant={statusVariant(index.status)}>{index.status}</Badge>
                {index.status_message && (
                  <span className="text-destructive text-xs">{index.status_message}</span>
                )}
              </span>
              <Button variant="ghost" size="sm" onClick={() => handleDelete(index.id)}>
                Delete
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
