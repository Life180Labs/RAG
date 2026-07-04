'use client';

import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useCreateRetrieval,
  useRetrieval,
  useRetrievalResults,
  useRetrievals,
} from '@/hooks/use-retrievals';
import { ApiRequestError } from '@/services/api-client';
import { SIMILARITY_METRICS, type RetrievalStatus, type SimilarityMetric } from '@/types/retrieval';

function statusVariant(status: RetrievalStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'failed') return 'destructive';
  if (status === 'completed') return 'default';
  return 'secondary';
}

export function RetrievalPlayground({
  documentId,
  vectorIndexId,
}: {
  documentId: string;
  vectorIndexId: string;
}) {
  const [queryText, setQueryText] = useState('');
  const [topK, setTopK] = useState(10);
  const [metric, setMetric] = useState<SimilarityMetric>('cosine');
  const [error, setError] = useState<string | null>(null);
  const [activeRetrievalId, setActiveRetrievalId] = useState<string | null>(null);
  const [showInspector, setShowInspector] = useState(false);

  const { data: history } = useRetrievals(documentId, vectorIndexId);
  const createRetrieval = useCreateRetrieval(documentId, vectorIndexId);
  const { data: activeRetrieval } = useRetrieval(documentId, vectorIndexId, activeRetrievalId);
  const { data: results, isLoading: resultsLoading } = useRetrievalResults(
    documentId,
    vectorIndexId,
    activeRetrievalId,
    showInspector && activeRetrieval?.status === 'completed',
  );

  async function handleSearch() {
    setError(null);
    setShowInspector(false);
    try {
      const response = await createRetrieval.mutateAsync({
        query_text: queryText,
        top_k: topK,
        similarity_metric: metric,
      });
      setActiveRetrievalId(response.data.id);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to run this query.');
    }
  }

  return (
    <div className="border-border space-y-3 border-t pt-2 pl-4" data-testid="retrieval-playground">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          className="border-input h-8 min-w-[240px] flex-1 rounded-lg border bg-transparent px-2 text-sm"
          placeholder="Ask a question…"
          value={queryText}
          onChange={(event) => setQueryText(event.target.value)}
          data-testid="retrieval-query-input"
        />
        <input
          className="border-input h-8 w-16 rounded-lg border bg-transparent px-2 text-sm"
          type="number"
          min={1}
          max={100}
          value={topK}
          onChange={(event) => setTopK(Number(event.target.value))}
          data-testid="retrieval-top-k-input"
        />
        <select
          className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
          value={metric}
          onChange={(event) => setMetric(event.target.value as SimilarityMetric)}
          data-testid="retrieval-metric-select"
        >
          {SIMILARITY_METRICS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          onClick={handleSearch}
          disabled={createRetrieval.isPending || queryText.trim().length === 0}
        >
          {createRetrieval.isPending ? 'Searching…' : 'Search'}
        </Button>
      </div>

      {activeRetrieval && (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="retrieval-summary">
          <Badge variant={statusVariant(activeRetrieval.status)}>{activeRetrieval.status}</Badge>
          {activeRetrieval.status === 'completed' && (
            <>
              <span className="text-muted-foreground text-xs">
                {activeRetrieval.result_count} results
              </span>
              {activeRetrieval.avg_similarity !== null && (
                <span className="text-muted-foreground text-xs">
                  avg similarity {activeRetrieval.avg_similarity.toFixed(3)}
                </span>
              )}
              {activeRetrieval.latency_ms !== null && (
                <span className="text-muted-foreground text-xs">
                  {activeRetrieval.latency_ms}ms
                </span>
              )}
              <Button size="sm" variant="ghost" onClick={() => setShowInspector((prev) => !prev)}>
                {showInspector ? 'Hide results' : 'Inspect results'}
              </Button>
            </>
          )}
          {activeRetrieval.status === 'failed' && activeRetrieval.status_message && (
            <span className="text-destructive text-xs">{activeRetrieval.status_message}</span>
          )}
        </div>
      )}

      {showInspector && resultsLoading && (
        <Skeleton className="h-8 w-full" data-testid="retrieval-results-loading" />
      )}

      {showInspector && results && results.length > 0 && (
        <ul className="divide-border divide-y text-sm" data-testid="retrieval-results-list">
          {results.map((result) => (
            <li key={result.id} className="space-y-1 py-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground text-xs">#{result.rank}</span>
                <span className="font-medium">score {result.score.toFixed(3)}</span>
                {result.chunk_heading && (
                  <span className="text-muted-foreground text-xs">{result.chunk_heading}</span>
                )}
                {result.chunk_page !== null && (
                  <span className="text-muted-foreground text-xs">p.{result.chunk_page}</span>
                )}
              </div>
              <p className="text-muted-foreground text-xs">{result.chunk_text}</p>
            </li>
          ))}
        </ul>
      )}

      {showInspector && results && results.length === 0 && (
        <p className="text-muted-foreground text-xs" data-testid="retrieval-results-empty">
          No results above the configured threshold.
        </p>
      )}

      {history && history.length > 0 && (
        <div className="space-y-1" data-testid="retrieval-history">
          <p className="text-muted-foreground text-xs">Recent queries</p>
          <ul className="divide-border divide-y text-sm">
            {history.map((retrieval) => (
              <li
                key={retrieval.id}
                className="flex flex-wrap items-center justify-between gap-2 py-1"
              >
                <button
                  type="button"
                  className="cursor-pointer truncate text-left underline-offset-2 hover:underline"
                  onClick={() => {
                    setActiveRetrievalId(retrieval.id);
                    setShowInspector(false);
                  }}
                >
                  {retrieval.query_text}
                </button>
                <Badge variant={statusVariant(retrieval.status)}>{retrieval.status}</Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
