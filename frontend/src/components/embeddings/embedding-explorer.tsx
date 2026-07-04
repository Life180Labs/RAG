'use client';

import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useCompareEmbeddingVersions,
  useDeleteEmbeddingVersion,
  useEmbeddings,
  useEmbeddingVersions,
  useGenerateEmbeddings,
} from '@/hooks/use-embeddings';
import { ApiRequestError } from '@/services/api-client';
import {
  EMBEDDING_PROVIDERS,
  type EmbeddingProviderName,
  type EmbeddingVersionStatus,
} from '@/types/embedding';

function statusVariant(status: EmbeddingVersionStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'failed') return 'destructive';
  if (status === 'ready') return 'default';
  return 'secondary';
}

function formatCost(cost: number | null): string {
  if (cost === null) return 'free';
  return `$${cost.toFixed(6)}`;
}

export function EmbeddingExplorer({
  documentId,
  chunkSetId,
}: {
  documentId: string;
  chunkSetId: string;
}) {
  const [selectedProvider, setSelectedProvider] = useState<EmbeddingProviderName>('bge');
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: versions, isLoading } = useEmbeddingVersions(documentId, chunkSetId);
  const generateEmbeddings = useGenerateEmbeddings(documentId, chunkSetId);
  const deleteEmbeddingVersion = useDeleteEmbeddingVersion(documentId, chunkSetId);
  const { data: embeddings, isLoading: isEmbeddingsLoading } = useEmbeddings(
    documentId,
    chunkSetId,
    expandedVersionId,
  );
  const { data: comparison } = useCompareEmbeddingVersions(
    documentId,
    chunkSetId,
    compareA,
    compareB,
  );

  async function handleGenerate() {
    setError(null);
    try {
      await generateEmbeddings.mutateAsync(selectedProvider);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to generate embeddings.');
    }
  }

  async function handleDelete(embeddingVersionId: string) {
    setError(null);
    try {
      await deleteEmbeddingVersion.mutateAsync(embeddingVersionId);
      if (expandedVersionId === embeddingVersionId) setExpandedVersionId(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to delete this version.');
    }
  }

  function toggleCompare(side: 'a' | 'b', provider: string) {
    if (side === 'a') setCompareA(compareA === provider ? null : provider);
    else setCompareB(compareB === provider ? null : provider);
  }

  return (
    <div className="border-border space-y-3 border-t pt-3" data-testid="embedding-explorer">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-2">
        <select
          className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
          value={selectedProvider}
          onChange={(event) => setSelectedProvider(event.target.value as EmbeddingProviderName)}
          data-testid="embedding-provider-select"
        >
          {EMBEDDING_PROVIDERS.map((provider) => (
            <option key={provider.value} value={provider.value}>
              {provider.label}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={handleGenerate} disabled={generateEmbeddings.isPending}>
          {generateEmbeddings.isPending ? 'Requesting…' : 'Generate embeddings'}
        </Button>
      </div>

      {generateEmbeddings.isSuccess && (
        <p className="text-muted-foreground text-xs" data-testid="embedding-generate-success">
          Embedding with &quot;{generateEmbeddings.data.data.provider}&quot; queued — it will appear
          below once the worker finishes.
        </p>
      )}

      {isLoading && <Skeleton className="h-12 w-full" data-testid="embedding-versions-loading" />}

      {versions && versions.length === 0 && (
        <p className="text-muted-foreground text-sm" data-testid="embedding-versions-empty">
          No embeddings generated yet.
        </p>
      )}

      {versions && versions.length > 0 && (
        <ul className="divide-border divide-y text-sm" data-testid="embedding-versions-list">
          {versions.map((version) => (
            <li key={version.id} className="space-y-2 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <button
                  type="button"
                  className="flex flex-wrap items-center gap-2 text-left"
                  onClick={() =>
                    setExpandedVersionId(expandedVersionId === version.id ? null : version.id)
                  }
                >
                  <span className="font-medium">{version.provider}</span>
                  <span className="text-muted-foreground text-xs">{version.model}</span>
                  <span className="text-muted-foreground text-xs">
                    {version.embedding_count} vectors · {version.dimensions}d
                  </span>
                  <span className="text-muted-foreground text-xs">
                    {formatCost(version.total_cost_usd)}
                    {version.avg_latency_ms !== null ? ` · ${version.avg_latency_ms}ms avg` : ''}
                  </span>
                  <Badge variant={statusVariant(version.status)}>{version.status}</Badge>
                </button>
                <div className="flex gap-1">
                  <Button
                    variant={compareA === version.provider ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => toggleCompare('a', version.provider)}
                  >
                    {compareA === version.provider ? 'Unset A' : 'Set A'}
                  </Button>
                  <Button
                    variant={compareB === version.provider ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => toggleCompare('b', version.provider)}
                  >
                    {compareB === version.provider ? 'Unset B' : 'Set B'}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(version.id)}>
                    Delete
                  </Button>
                </div>
              </div>

              {expandedVersionId === version.id && (
                <div className="bg-muted/30 rounded-lg p-2" data-testid="embedding-list-panel">
                  {isEmbeddingsLoading && <Skeleton className="h-8 w-full" />}
                  {embeddings && (
                    <ul className="space-y-1" data-testid="embedding-list">
                      {embeddings.map((embedding) => (
                        <li key={embedding.id} className="text-muted-foreground text-xs">
                          chunk {embedding.chunk_id.slice(0, 8)} · {embedding.token_count} tokens ·{' '}
                          {embedding.latency_ms}ms · {formatCost(embedding.cost_usd)} ·{' '}
                          {embedding.status}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {compareA && compareB && comparison && (
        <div
          className="grid grid-cols-1 gap-3 border-t pt-3 sm:grid-cols-2"
          data-testid="embedding-comparison"
        >
          <div>
            <h4 className="text-sm font-medium">
              {comparison.version_a.provider} ({comparison.version_a.model})
            </h4>
            <p className="text-muted-foreground text-xs">
              {comparison.version_a.embedding_count} vectors · {comparison.version_a.dimensions}d ·{' '}
              {formatCost(comparison.version_a.total_cost_usd)}
            </p>
          </div>
          <div>
            <h4 className="text-sm font-medium">
              {comparison.version_b.provider} ({comparison.version_b.model})
            </h4>
            <p className="text-muted-foreground text-xs">
              {comparison.version_b.embedding_count} vectors · {comparison.version_b.dimensions}d ·{' '}
              {formatCost(comparison.version_b.total_cost_usd)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
