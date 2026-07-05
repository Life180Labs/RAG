'use client';

import { useMemo, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useCompletions, useCreateCompletion, useModels } from '@/hooks/use-llm';
import { ApiRequestError } from '@/services/api-client';
import { ROUTING_HINTS, type LLMRequestStatus, type RoutingHint } from '@/types/llm';

function statusVariant(status: LLMRequestStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'failed') return 'destructive';
  if (status === 'completed') return 'default';
  return 'secondary';
}

export function LLMCompletionPanel({
  documentId,
  vectorIndexId,
  retrievalId,
  promptId,
}: {
  documentId: string;
  vectorIndexId: string;
  retrievalId: string;
  promptId: string;
}) {
  const { data: models } = useModels();
  const { data: completions } = useCompletions(documentId, vectorIndexId, retrievalId, promptId);
  const createCompletion = useCreateCompletion(documentId, vectorIndexId, retrievalId, promptId);

  const [useExplicitModel, setUseExplicitModel] = useState(false);
  const [selectedModelKey, setSelectedModelKey] = useState('');
  const [routingHint, setRoutingHint] = useState<RoutingHint | ''>('');
  const [error, setError] = useState<string | null>(null);

  const latest = completions && completions.length > 0 ? completions[0] : null;

  const totals = useMemo(() => {
    if (!completions || completions.length === 0) return null;
    const totalCost = completions.reduce((sum, c) => sum + (c.cost_usd ?? 0), 0);
    const latencies = completions.map((c) => c.latency_ms).filter((v): v is number => v !== null);
    const avgLatency =
      latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : null;
    return { totalCost, avgLatency, count: completions.length };
  }, [completions]);

  async function handleGenerate() {
    setError(null);
    try {
      if (useExplicitModel && selectedModelKey) {
        const [provider, model] = selectedModelKey.split('::');
        await createCompletion.mutateAsync({ provider, model });
      } else {
        await createCompletion.mutateAsync({ routing_hint: routingHint || undefined });
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to generate a completion.');
    }
  }

  return (
    <div className="border-border space-y-3 border-t pt-2 pl-4" data-testid="llm-completion-panel">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={useExplicitModel}
            onChange={(event) => setUseExplicitModel(event.target.checked)}
            data-testid="llm-use-explicit-model-toggle"
          />
          <span className="text-muted-foreground">Choose a specific model</span>
        </label>
      </div>

      {useExplicitModel ? (
        <select
          className="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-sm"
          value={selectedModelKey}
          onChange={(event) => setSelectedModelKey(event.target.value)}
          data-testid="llm-model-select"
        >
          <option value="">Select a model…</option>
          {models?.map((model) => (
            <option
              key={`${model.provider}::${model.model}`}
              value={`${model.provider}::${model.model}`}
            >
              {model.provider} / {model.model}
              {model.price_per_1m_input === 0 ? ' (free)' : ''}
            </option>
          ))}
        </select>
      ) : (
        <select
          className="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-sm"
          value={routingHint}
          onChange={(event) => setRoutingHint(event.target.value as RoutingHint | '')}
          data-testid="llm-routing-hint-select"
        >
          <option value="">Default model</option>
          {ROUTING_HINTS.map((hint) => (
            <option key={hint.value} value={hint.value}>
              {hint.label}
            </option>
          ))}
        </select>
      )}

      <Button
        size="sm"
        onClick={handleGenerate}
        disabled={createCompletion.isPending || (useExplicitModel && !selectedModelKey)}
        data-testid="llm-generate-button"
      >
        {createCompletion.isPending ? 'Generating…' : 'Generate completion'}
      </Button>

      {latest && (
        <div
          className="border-border space-y-2 rounded-lg border p-2"
          data-testid="llm-latest-completion"
        >
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={statusVariant(latest.status)}>{latest.status}</Badge>
            <Badge variant="secondary">
              {latest.provider} / {latest.model}
            </Badge>
            {latest.cost_usd !== null && (
              <span className="text-muted-foreground text-xs" data-testid="llm-latest-cost">
                ${latest.cost_usd.toFixed(6)}
              </span>
            )}
            {latest.latency_ms !== null && (
              <span className="text-muted-foreground text-xs">{latest.latency_ms}ms</span>
            )}
            <span className="text-muted-foreground text-xs">
              {latest.input_tokens} in / {latest.output_tokens} out
            </span>
          </div>

          {latest.status === 'failed' && latest.status_message && (
            <p className="text-destructive text-xs">{latest.status_message}</p>
          )}

          {latest.output_text && (
            <pre
              className="border-border bg-muted/40 max-h-64 overflow-auto rounded-lg border p-2 text-xs whitespace-pre-wrap"
              data-testid="llm-output-text"
            >
              {latest.output_text}
            </pre>
          )}

          {latest.attempted_providers && latest.attempted_providers.length > 1 && (
            <div className="text-xs" data-testid="llm-attempted-providers">
              <span className="text-muted-foreground">Fallback trail: </span>
              {latest.attempted_providers.map((attempt, index) => (
                <span key={`${attempt.provider}-${index}`} className="mr-2">
                  <Badge variant={attempt.error ? 'destructive' : 'default'}>
                    {attempt.provider}
                  </Badge>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {totals && (
        <div
          className="flex flex-wrap items-center gap-3 text-xs"
          data-testid="llm-completion-dashboard"
        >
          <span className="text-muted-foreground">
            {totals.count} completion{totals.count === 1 ? '' : 's'}
          </span>
          <span className="text-muted-foreground" data-testid="llm-total-cost">
            total cost ${totals.totalCost.toFixed(6)}
          </span>
          {totals.avgLatency !== null && (
            <span className="text-muted-foreground" data-testid="llm-avg-latency">
              avg latency {Math.round(totals.avgLatency)}ms
            </span>
          )}
        </div>
      )}

      {completions && completions.length > 1 && (
        <ul className="divide-border divide-y text-xs" data-testid="llm-completion-history">
          {completions.map((completion) => (
            <li key={completion.id} className="flex flex-wrap items-center gap-2 py-1">
              <Badge variant={statusVariant(completion.status)}>{completion.status}</Badge>
              <span>
                {completion.provider} / {completion.model}
              </span>
              {completion.cost_usd !== null && <span>${completion.cost_usd.toFixed(6)}</span>}
              {completion.latency_ms !== null && <span>{completion.latency_ms}ms</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
