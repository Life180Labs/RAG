'use client';

import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmbeddingExplorer } from '@/components/embeddings/embedding-explorer';
import {
  useChunkSets,
  useChunks,
  useCompareChunkSets,
  useDeleteChunkSet,
  useGenerateChunks,
} from '@/hooks/use-chunks';
import { ApiRequestError } from '@/services/api-client';
import { CHUNK_STRATEGIES, type ChunkSetStatus, type ChunkStrategy } from '@/types/chunk';

function statusVariant(status: ChunkSetStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'failed') return 'destructive';
  if (status === 'ready') return 'default';
  return 'secondary';
}

export function ChunkExplorer({ documentId }: { documentId: string }) {
  const [selectedStrategy, setSelectedStrategy] = useState<ChunkStrategy>('recursive');
  const [expandedSetId, setExpandedSetId] = useState<string | null>(null);
  const [expandedEmbeddingsSetId, setExpandedEmbeddingsSetId] = useState<string | null>(null);
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: chunkSets, isLoading } = useChunkSets(documentId);
  const generateChunks = useGenerateChunks(documentId);
  const deleteChunkSet = useDeleteChunkSet(documentId);
  const { data: chunks, isLoading: isChunksLoading } = useChunks(documentId, expandedSetId);
  const { data: comparison } = useCompareChunkSets(documentId, compareA, compareB);

  async function handleGenerate() {
    setError(null);
    try {
      await generateChunks.mutateAsync(selectedStrategy);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to generate chunks.');
    }
  }

  async function handleDelete(chunkSetId: string) {
    setError(null);
    try {
      await deleteChunkSet.mutateAsync(chunkSetId);
      if (expandedSetId === chunkSetId) setExpandedSetId(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to delete this chunk set.');
    }
  }

  function toggleCompare(side: 'a' | 'b', strategy: string) {
    if (side === 'a') setCompareA(compareA === strategy ? null : strategy);
    else setCompareB(compareB === strategy ? null : strategy);
  }

  return (
    <div className="border-border space-y-3 border-t pt-3" data-testid="chunk-explorer">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center gap-2">
        <select
          className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
          value={selectedStrategy}
          onChange={(event) => setSelectedStrategy(event.target.value as ChunkStrategy)}
          data-testid="chunk-strategy-select"
        >
          {CHUNK_STRATEGIES.map((strategy) => (
            <option key={strategy.value} value={strategy.value}>
              {strategy.label}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={handleGenerate} disabled={generateChunks.isPending}>
          {generateChunks.isPending ? 'Requesting…' : 'Generate chunks'}
        </Button>
      </div>

      {generateChunks.isSuccess && (
        <p className="text-muted-foreground text-xs" data-testid="chunk-generate-success">
          Chunking with &quot;{generateChunks.data.data.strategy}&quot; queued — it will appear
          below once the worker finishes.
        </p>
      )}

      {isLoading && <Skeleton className="h-12 w-full" data-testid="chunk-sets-loading" />}

      {chunkSets && chunkSets.length === 0 && (
        <p className="text-muted-foreground text-sm" data-testid="chunk-sets-empty">
          No chunks generated yet.
        </p>
      )}

      {chunkSets && chunkSets.length > 0 && (
        <ul className="divide-border divide-y text-sm" data-testid="chunk-sets-list">
          {chunkSets.map((set) => (
            <li key={set.id} className="space-y-2 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <button
                  type="button"
                  className="flex items-center gap-2 text-left"
                  onClick={() => setExpandedSetId(expandedSetId === set.id ? null : set.id)}
                >
                  <span className="font-medium">{set.strategy}</span>
                  <span className="text-muted-foreground text-xs">{set.chunk_count} chunks</span>
                  <Badge variant={statusVariant(set.status)}>{set.status}</Badge>
                </button>
                <div className="flex gap-1">
                  <Button
                    variant={compareA === set.strategy ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => toggleCompare('a', set.strategy)}
                  >
                    {compareA === set.strategy ? 'Unset A' : 'Set A'}
                  </Button>
                  <Button
                    variant={compareB === set.strategy ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => toggleCompare('b', set.strategy)}
                  >
                    {compareB === set.strategy ? 'Unset B' : 'Set B'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setExpandedEmbeddingsSetId(expandedEmbeddingsSetId === set.id ? null : set.id)
                    }
                  >
                    Embeddings
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(set.id)}>
                    Delete
                  </Button>
                </div>
              </div>

              {expandedSetId === set.id && (
                <div className="bg-muted/30 rounded-lg p-2" data-testid="chunk-list-panel">
                  {isChunksLoading && <Skeleton className="h-8 w-full" />}
                  {chunks && (
                    <ul className="space-y-2" data-testid="chunk-list">
                      {chunks.map((chunk) => (
                        <li key={chunk.id} className="text-xs">
                          <span className="text-muted-foreground">
                            #{chunk.chunk_index} · {chunk.token_count} tokens
                            {chunk.heading ? ` · ${chunk.heading}` : ''}
                          </span>
                          <p className="whitespace-pre-wrap">{chunk.text}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {expandedEmbeddingsSetId === set.id && (
                <EmbeddingExplorer documentId={documentId} chunkSetId={set.id} />
              )}
            </li>
          ))}
        </ul>
      )}

      {compareA && compareB && comparison && (
        <div
          className="grid grid-cols-1 gap-3 border-t pt-3 sm:grid-cols-2"
          data-testid="chunk-comparison"
        >
          <div>
            <h4 className="text-sm font-medium">{comparison.strategy_a.strategy}</h4>
            <ul className="space-y-2">
              {comparison.chunks_a.map((chunk) => (
                <li key={chunk.id} className="text-xs">
                  <span className="text-muted-foreground">
                    #{chunk.chunk_index} · {chunk.token_count} tok
                  </span>
                  <p className="whitespace-pre-wrap">{chunk.text}</p>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-medium">{comparison.strategy_b.strategy}</h4>
            <ul className="space-y-2">
              {comparison.chunks_b.map((chunk) => (
                <li key={chunk.id} className="text-xs">
                  <span className="text-muted-foreground">
                    #{chunk.chunk_index} · {chunk.token_count} tok
                  </span>
                  <p className="whitespace-pre-wrap">{chunk.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
