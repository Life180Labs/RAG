'use client';

import { useMemo, useState } from 'react';

import { LLMCompletionPanel } from '@/components/llm/llm-completion-panel';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useDocument } from '@/hooks/use-documents';
import {
  useArchivePromptTemplate,
  useBuildPrompt,
  useCreatePromptTemplate,
  usePromptTemplateVersions,
  usePromptTemplates,
  usePrompts,
} from '@/hooks/use-prompts';
import { diffWords } from '@/lib/text-diff';
import { ApiRequestError } from '@/services/api-client';
import type { PromptStatus } from '@/types/prompt';

function statusVariant(status: PromptStatus): 'default' | 'secondary' | 'destructive' {
  if (status === 'failed') return 'destructive';
  if (status === 'completed') return 'default';
  return 'secondary';
}

function TokenBar({ label, value, testId }: { label: string; value: number; testId?: string }) {
  return (
    <span className="text-muted-foreground text-xs" data-testid={testId}>
      {label} {value}
    </span>
  );
}

export function PromptPlayground({
  documentId,
  vectorIndexId,
  retrievalId,
}: {
  documentId: string;
  vectorIndexId: string;
  retrievalId: string;
}) {
  const { data: document } = useDocument(documentId);
  const repositoryId = document?.repository_id ?? null;

  const { data: templates } = usePromptTemplates(repositoryId);
  const { data: prompts } = usePrompts(documentId, vectorIndexId, retrievalId);
  const createTemplate = useCreatePromptTemplate(repositoryId ?? '');
  const archiveTemplate = useArchivePromptTemplate(repositoryId ?? '');
  const buildPrompt = useBuildPrompt(documentId, vectorIndexId, retrievalId);

  const [useTemplate, setUseTemplate] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [inlineSystemPrompt, setInlineSystemPrompt] = useState(
    'You are an enterprise assistant. Answer only using the supplied context.',
  );
  const [modelContextWindow, setModelContextWindow] = useState(8192);
  const [orderByPage, setOrderByPage] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateSystemPrompt, setNewTemplateSystemPrompt] = useState('');
  const [showNewTemplateForm, setShowNewTemplateForm] = useState(false);

  const [historyName, setHistoryName] = useState<string | null>(null);
  const { data: versions } = usePromptTemplateVersions(repositoryId, historyName);
  const [diffLeftId, setDiffLeftId] = useState('');
  const [diffRightId, setDiffRightId] = useState('');

  const latestByName = useMemo(() => {
    if (!templates) return [];
    const byName = new Map<string, (typeof templates)[number]>();
    for (const template of templates) {
      const current = byName.get(template.name);
      if (!current || template.version > current.version) byName.set(template.name, template);
    }
    return Array.from(byName.values());
  }, [templates]);

  const diffLeft = versions?.find((v) => v.id === diffLeftId) ?? null;
  const diffRight = versions?.find((v) => v.id === diffRightId) ?? null;
  const diffTokens =
    diffLeft && diffRight ? diffWords(diffLeft.system_prompt, diffRight.system_prompt) : null;

  async function handleCreateTemplate() {
    if (!repositoryId) return;
    setError(null);
    try {
      await createTemplate.mutateAsync({
        name: newTemplateName,
        system_prompt: newTemplateSystemPrompt,
      });
      setNewTemplateName('');
      setNewTemplateSystemPrompt('');
      setShowNewTemplateForm(false);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create template.');
    }
  }

  async function handleBuild() {
    setError(null);
    try {
      await buildPrompt.mutateAsync({
        ...(useTemplate && selectedTemplateId
          ? { prompt_template_id: selectedTemplateId }
          : { system_prompt: inlineSystemPrompt }),
        model_context_window: modelContextWindow,
        order_by_page: orderByPage,
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to build this prompt.');
    }
  }

  const latestPrompt = prompts && prompts.length > 0 ? prompts[0] : null;

  return (
    <div className="border-border space-y-3 border-t pt-2 pl-4" data-testid="prompt-playground">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={useTemplate}
            onChange={(event) => setUseTemplate(event.target.checked)}
            data-testid="prompt-use-template-toggle"
          />
          <span className="text-muted-foreground">Use saved template</span>
        </label>

        <label className="flex items-center gap-2">
          <span className="text-muted-foreground">Context window</span>
          <input
            className="border-input h-8 w-20 rounded-lg border bg-transparent px-2 text-sm"
            type="number"
            min={256}
            value={modelContextWindow}
            onChange={(event) => setModelContextWindow(Number(event.target.value))}
            data-testid="prompt-context-window-input"
          />
        </label>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={orderByPage}
            onChange={(event) => setOrderByPage(event.target.checked)}
            data-testid="prompt-order-by-page-toggle"
          />
          <span className="text-muted-foreground">Order context by page</span>
        </label>
      </div>

      {useTemplate ? (
        <select
          className="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-sm"
          value={selectedTemplateId}
          onChange={(event) => setSelectedTemplateId(event.target.value)}
          data-testid="prompt-template-select"
        >
          <option value="">Select a template…</option>
          {latestByName.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name} (v{template.version})
            </option>
          ))}
        </select>
      ) : (
        <textarea
          className="border-input min-h-[72px] w-full rounded-lg border bg-transparent px-2 py-1 text-sm"
          placeholder="System prompt…"
          value={inlineSystemPrompt}
          onChange={(event) => setInlineSystemPrompt(event.target.value)}
          data-testid="prompt-inline-system-prompt-input"
        />
      )}

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          onClick={handleBuild}
          disabled={
            buildPrompt.isPending ||
            (useTemplate ? !selectedTemplateId : !inlineSystemPrompt.trim())
          }
          data-testid="prompt-build-button"
        >
          {buildPrompt.isPending ? 'Building…' : 'Build prompt'}
        </Button>
        {!showNewTemplateForm && (
          <Button size="sm" variant="ghost" onClick={() => setShowNewTemplateForm(true)}>
            Save new template
          </Button>
        )}
      </div>

      {showNewTemplateForm && (
        <div
          className="border-border space-y-2 rounded-lg border p-2"
          data-testid="prompt-new-template-form"
        >
          <input
            className="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-sm"
            placeholder="Template name"
            value={newTemplateName}
            onChange={(event) => setNewTemplateName(event.target.value)}
            data-testid="prompt-new-template-name-input"
          />
          <textarea
            className="border-input min-h-[60px] w-full rounded-lg border bg-transparent px-2 py-1 text-sm"
            placeholder="System prompt for this template…"
            value={newTemplateSystemPrompt}
            onChange={(event) => setNewTemplateSystemPrompt(event.target.value)}
            data-testid="prompt-new-template-system-prompt-input"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleCreateTemplate}
              disabled={
                createTemplate.isPending ||
                !newTemplateName.trim() ||
                !newTemplateSystemPrompt.trim()
              }
            >
              {createTemplate.isPending ? 'Saving…' : 'Save version 1'}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowNewTemplateForm(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {latestPrompt && (
        <div className="border-border space-y-2 rounded-lg border p-2" data-testid="prompt-result">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={statusVariant(latestPrompt.status)}>{latestPrompt.status}</Badge>
            <TokenBar
              label="system"
              value={latestPrompt.system_prompt_tokens}
              testId="prompt-tokens-system"
            />
            <TokenBar label="context" value={latestPrompt.context_tokens} />
            <TokenBar label="query" value={latestPrompt.query_tokens} />
            <TokenBar label="response reserve" value={latestPrompt.response_budget_tokens} />
            <TokenBar
              label="total /"
              value={latestPrompt.total_tokens}
              testId="prompt-tokens-total"
            />
            <span className="text-muted-foreground text-xs">
              {latestPrompt.model_context_window} window
            </span>
          </div>

          {latestPrompt.status === 'failed' && latestPrompt.status_message && (
            <p className="text-destructive text-xs" data-testid="prompt-error-message">
              {latestPrompt.status_message}
            </p>
          )}

          {latestPrompt.rendered_prompt && (
            <pre
              className="border-border bg-muted/40 max-h-64 overflow-auto rounded-lg border p-2 text-xs whitespace-pre-wrap"
              data-testid="prompt-rendered-text"
            >
              {latestPrompt.rendered_prompt}
            </pre>
          )}

          {latestPrompt.citations && latestPrompt.citations.length > 0 && (
            <ul className="space-y-1 text-xs" data-testid="prompt-citations-list">
              {latestPrompt.citations.map((citation) => (
                <li key={citation.chunk_id} className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{citation.source_label}</Badge>
                  <span>{citation.document_filename}</span>
                  {citation.page !== null && (
                    <span className="text-muted-foreground">p.{citation.page}</span>
                  )}
                  {citation.section && (
                    <span className="text-muted-foreground">{citation.section}</span>
                  )}
                  <span className="text-muted-foreground">
                    confidence {citation.confidence.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {latestPrompt && latestPrompt.status === 'completed' && (
        <LLMCompletionPanel
          documentId={documentId}
          vectorIndexId={vectorIndexId}
          retrievalId={retrievalId}
          promptId={latestPrompt.id}
        />
      )}

      {latestByName.length > 0 && (
        <div className="space-y-2" data-testid="prompt-version-history">
          <p className="text-muted-foreground text-xs">Version history</p>
          <select
            className="border-input h-8 rounded-lg border bg-transparent px-2 text-sm"
            value={historyName ?? ''}
            onChange={(event) => setHistoryName(event.target.value || null)}
            data-testid="prompt-history-template-select"
          >
            <option value="">Select a template…</option>
            {latestByName.map((template) => (
              <option key={template.name} value={template.name}>
                {template.name}
              </option>
            ))}
          </select>

          {versions && versions.length > 0 && (
            <ul className="divide-border divide-y text-xs" data-testid="prompt-version-list">
              {versions.map((version) => (
                <li key={version.id} className="flex items-center justify-between gap-2 py-1">
                  <span>
                    v{version.version}
                    {!version.is_active && (
                      <span className="text-muted-foreground"> (archived)</span>
                    )}
                  </span>
                  <span className="flex items-center gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setDiffLeftId(version.id)}>
                      Diff A
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setDiffRightId(version.id)}>
                      Diff B
                    </Button>
                    {version.is_active && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => archiveTemplate.mutate(version.id)}
                      >
                        Archive
                      </Button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {diffTokens && (
            <div
              className="border-border rounded-lg border p-2 text-xs leading-relaxed"
              data-testid="prompt-template-diff"
            >
              <p className="text-muted-foreground mb-1">
                Diff: v{diffLeft?.version} → v{diffRight?.version}
              </p>
              {diffTokens.map((token, index) => (
                <span
                  key={index}
                  className={
                    token.type === 'added'
                      ? 'bg-green-500/20 text-green-700 dark:text-green-400'
                      : token.type === 'removed'
                        ? 'bg-red-500/20 text-red-700 line-through dark:text-red-400'
                        : ''
                  }
                >
                  {token.value}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
