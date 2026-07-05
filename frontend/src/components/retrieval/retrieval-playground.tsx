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
import {
  FUSION_METHODS,
  QUERY_INTENT_LABELS,
  SIMILARITY_METRICS,
  type FusionMethod,
  type RetrievalMode,
  type RetrievalStatus,
  type SimilarityMetric,
} from '@/types/retrieval';

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
  const [mode, setMode] = useState<RetrievalMode>('dense');
  const [fusionMethod, setFusionMethod] = useState<FusionMethod>('weighted_sum');
  const [denseWeight, setDenseWeight] = useState(0.7);
  const [rrfK, setRrfK] = useState(60);
  const [queryUnderstandingEnabled, setQueryUnderstandingEnabled] = useState(false);
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
        retrieval_mode: mode,
        query_understanding_enabled: queryUnderstandingEnabled,
        ...(mode === 'hybrid'
          ? {
              fusion_method: fusionMethod,
              ...(fusionMethod === 'weighted_sum'
                ? { dense_weight: denseWeight, sparse_weight: 1 - denseWeight }
                : { rrf_k: rrfK }),
            }
          : {}),
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

      <label className="flex items-center gap-2 text-xs" data-testid="query-understanding-toggle">
        <input
          type="checkbox"
          checked={queryUnderstandingEnabled}
          onChange={(event) => setQueryUnderstandingEnabled(event.target.checked)}
        />
        <span className="text-muted-foreground">
          Query understanding (classify, rewrite, expand, extract filters)
        </span>
      </label>

      <div className="flex flex-wrap items-center gap-2" data-testid="hybrid-search-dashboard">
        <div className="flex items-center gap-1 text-sm">
          <button
            type="button"
            className={`h-8 rounded-lg border px-3 ${mode === 'dense' ? 'bg-primary text-primary-foreground' : 'border-input bg-transparent'}`}
            onClick={() => setMode('dense')}
            data-testid="retrieval-mode-dense"
          >
            Dense
          </button>
          <button
            type="button"
            className={`h-8 rounded-lg border px-3 ${mode === 'hybrid' ? 'bg-primary text-primary-foreground' : 'border-input bg-transparent'}`}
            onClick={() => setMode('hybrid')}
            data-testid="retrieval-mode-hybrid"
          >
            Hybrid
          </button>
        </div>

        {mode === 'hybrid' && (
          <>
            <select
              className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
              value={fusionMethod}
              onChange={(event) => setFusionMethod(event.target.value as FusionMethod)}
              data-testid="retrieval-fusion-method-select"
            >
              {FUSION_METHODS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            {fusionMethod === 'weighted_sum' && (
              <label className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">
                  dense {denseWeight.toFixed(2)} / sparse {(1 - denseWeight).toFixed(2)}
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={denseWeight}
                  onChange={(event) => setDenseWeight(Number(event.target.value))}
                  data-testid="retrieval-weight-slider"
                />
              </label>
            )}

            {fusionMethod === 'rrf' && (
              <label className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">k</span>
                <input
                  className="border-input h-8 w-16 rounded-lg border bg-transparent px-2 text-sm"
                  type="number"
                  min={1}
                  value={rrfK}
                  onChange={(event) => setRrfK(Number(event.target.value))}
                  data-testid="retrieval-rrf-k-input"
                />
              </label>
            )}
          </>
        )}
      </div>

      {activeRetrieval && (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="retrieval-summary">
          <Badge variant={statusVariant(activeRetrieval.status)}>{activeRetrieval.status}</Badge>
          <Badge variant="secondary">{activeRetrieval.retrieval_mode}</Badge>
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

      {activeRetrieval?.query_understanding_enabled && activeRetrieval.status === 'completed' && (
        <div
          className="border-border space-y-1 rounded-lg border p-2 text-xs"
          data-testid="query-inspector"
        >
          {activeRetrieval.query_intent && (
            <div className="flex items-center gap-2" data-testid="query-inspector-intent">
              <span className="text-muted-foreground">Intent</span>
              <Badge variant="secondary">{QUERY_INTENT_LABELS[activeRetrieval.query_intent]}</Badge>
              {activeRetrieval.intent_confidence !== null && (
                <span className="text-muted-foreground">
                  {(activeRetrieval.intent_confidence * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>
          )}
          {activeRetrieval.rewritten_query_text && (
            <div data-testid="query-inspector-rewrite">
              <span className="text-muted-foreground">Rewritten </span>
              {activeRetrieval.rewritten_query_text}
            </div>
          )}
          {activeRetrieval.generated_queries && activeRetrieval.generated_queries.length > 1 && (
            <div data-testid="query-inspector-generated-queries">
              <span className="text-muted-foreground">Generated queries</span>
              <ul className="list-disc pl-4">
                {activeRetrieval.generated_queries.map((generated) => (
                  <li key={generated}>{generated}</li>
                ))}
              </ul>
            </div>
          )}
          {activeRetrieval.detected_metadata_filter && (
            <div className="flex flex-wrap items-center gap-1" data-testid="query-inspector-filter">
              <span className="text-muted-foreground">Detected filter</span>
              {Object.entries(activeRetrieval.detected_metadata_filter).map(([key, value]) => (
                <Badge key={key} variant="secondary">
                  {key}={value}
                </Badge>
              ))}
            </div>
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
                {result.dense_score !== null && (
                  <span
                    className="text-muted-foreground text-xs"
                    data-testid="retrieval-dense-score"
                  >
                    dense {result.dense_score.toFixed(3)}
                  </span>
                )}
                {result.sparse_score !== null && (
                  <span
                    className="text-muted-foreground text-xs"
                    data-testid="retrieval-sparse-score"
                  >
                    sparse {result.sparse_score.toFixed(3)}
                  </span>
                )}
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
                <span className="flex items-center gap-1">
                  <Badge variant="secondary">{retrieval.retrieval_mode}</Badge>
                  <Badge variant={statusVariant(retrieval.status)}>{retrieval.status}</Badge>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
