'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useUpdateRepositorySettings } from '@/hooks/use-repositories';
import { ApiRequestError } from '@/services/api-client';
import type { Repository, RepositorySettings } from '@/types/repository';

const SETTINGS_FIELDS: { key: keyof RepositorySettings; label: string }[] = [
  { key: 'default_chunk_strategy', label: 'Default chunk strategy' },
  { key: 'default_embedding_model', label: 'Default embedding model' },
  { key: 'default_retriever', label: 'Default retriever' },
  { key: 'default_reranker', label: 'Default reranker' },
  { key: 'default_prompt_version', label: 'Default prompt version' },
];

// Mounted only once `repository` has loaded (see RepositoryDashboard), so
// initializing state straight from the prop is safe — no effect needed to
// "sync" it in after the fact.
export function RepositorySettingsForm({ repository }: { repository: Repository }) {
  const [settings, setSettings] = useState<RepositorySettings>({
    default_chunk_strategy: repository.default_chunk_strategy ?? '',
    default_embedding_model: repository.default_embedding_model ?? '',
    default_retriever: repository.default_retriever ?? '',
    default_reranker: repository.default_reranker ?? '',
    default_prompt_version: repository.default_prompt_version ?? '',
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const updateSettings = useUpdateRepositorySettings(repository.id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    try {
      await updateSettings.mutateAsync({
        default_chunk_strategy: settings.default_chunk_strategy || null,
        default_embedding_model: settings.default_embedding_model || null,
        default_retriever: settings.default_retriever || null,
        default_reranker: settings.default_reranker || null,
        default_prompt_version: settings.default_prompt_version || null,
      });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to update settings.');
    }
  }

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t save settings</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert data-testid="repository-settings-success">
          <AlertTitle>Settings saved</AlertTitle>
        </Alert>
      )}
      {SETTINGS_FIELDS.map(({ key, label }) => (
        <div key={key} className="space-y-1">
          <Label htmlFor={key}>{label}</Label>
          <Input
            id={key}
            value={settings[key] ?? ''}
            onChange={(e) => setSettings((prev) => ({ ...prev, [key]: e.target.value }))}
          />
        </div>
      ))}
      <Button type="submit" disabled={updateSettings.isPending}>
        {updateSettings.isPending ? 'Saving…' : 'Save settings'}
      </Button>
    </form>
  );
}
