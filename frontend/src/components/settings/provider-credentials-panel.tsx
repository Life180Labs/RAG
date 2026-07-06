'use client';

import { useState } from 'react';
import { KeyRound, Plus, Trash2 } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useDeleteProviderCredential,
  useProviderCredentials,
  useUpsertProviderCredential,
} from '@/hooks/use-provider-credentials';
import { ApiRequestError } from '@/services/api-client';
import { PROVIDER_TYPES, type ProviderType } from '@/types/provider-credential';

function UpsertProviderCredentialForm({
  organizationId,
  onSaved,
}: {
  organizationId: string;
  onSaved: () => void;
}) {
  const [provider, setProvider] = useState<ProviderType>('openai');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const upsert = useUpsertProviderCredential(organizationId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await upsert.mutateAsync({ provider, api_key: apiKey });
      setApiKey('');
      onSaved();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to save this key.');
    }
  }

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t save key</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="space-y-1">
          <Label htmlFor="credential-provider">Provider</Label>
          <select
            id="credential-provider"
            className="border-input bg-background h-8 rounded-lg border px-2.5 text-sm"
            value={provider}
            onChange={(e) => setProvider(e.target.value as ProviderType)}
          >
            {PROVIDER_TYPES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 space-y-1">
          <Label htmlFor="credential-api-key">API key</Label>
          <Input
            id="credential-api-key"
            type="password"
            required
            autoComplete="off"
            placeholder="sk-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={upsert.isPending}>
          {upsert.isPending ? 'Saving…' : 'Save key'}
        </Button>
      </div>
    </form>
  );
}

export function ProviderCredentialsPanel({ organizationId }: { organizationId: string }) {
  const { data: credentials, isLoading, isError, error } = useProviderCredentials(organizationId);
  const [showAdd, setShowAdd] = useState(false);
  const deleteCredential = useDeleteProviderCredential(organizationId);

  return (
    <div className="w-full max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-foreground text-xl font-semibold">Settings</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            Configure this organization&apos;s LLM, embedding, reranking, and vector-index provider
            API keys. Configured keys take precedence over the platform&apos;s default keys for
            every request made on behalf of this organization.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowAdd((v) => !v)} className="gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          Add key
        </Button>
      </div>

      {showAdd && (
        <Card className="border-primary/20 bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Add or update a provider key</CardTitle>
          </CardHeader>
          <CardContent>
            <UpsertProviderCredentialForm
              organizationId={organizationId}
              onSaved={() => setShowAdd(false)}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wide uppercase">
            Provider API keys
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading && (
            <div className="space-y-px p-1" data-testid="provider-credentials-loading">
              <Skeleton className="h-14 w-full rounded-lg" />
              <Skeleton className="h-14 w-full rounded-lg" />
            </div>
          )}

          {isError && (
            <div className="p-4">
              <Alert variant="destructive">
                <AlertTitle>Couldn&apos;t load provider keys</AlertTitle>
                <AlertDescription>
                  {error instanceof Error ? error.message : 'Something went wrong.'}
                </AlertDescription>
              </Alert>
            </div>
          )}

          {credentials && credentials.length === 0 && (
            <div
              className="flex flex-col items-center justify-center py-12 text-center"
              data-testid="provider-credentials-empty"
            >
              <p className="text-foreground text-sm font-medium">No provider keys configured</p>
              <p className="text-muted-foreground mt-1 text-xs">
                Without a key, requests fall back to the platform&apos;s default keys, if any.
              </p>
              <Button
                size="sm"
                variant="outline"
                className="mt-4 gap-1.5"
                onClick={() => setShowAdd(true)}
              >
                <Plus className="h-3.5 w-3.5" />
                Add a key
              </Button>
            </div>
          )}

          {credentials && credentials.length > 0 && (
            <ul className="divide-border divide-y" data-testid="provider-credentials-list">
              {credentials.map((credential) => (
                <li key={credential.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex min-w-0 items-center gap-3">
                    <KeyRound className="text-muted-foreground/50 h-4 w-4 shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-foreground truncate text-sm font-medium">
                          {credential.provider}
                        </p>
                        <Badge variant="secondary">•••• {credential.last_four}</Badge>
                      </div>
                      <p className="text-muted-foreground text-xs">
                        Updated {new Date(credential.updated_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    title="Delete"
                    onClick={() => deleteCredential.mutate(credential.id)}
                    disabled={deleteCredential.isPending}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
