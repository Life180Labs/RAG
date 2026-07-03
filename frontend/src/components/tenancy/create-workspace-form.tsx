'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateWorkspace } from '@/hooks/use-tenancy';
import { slugify } from '@/lib/slug';
import { ApiRequestError } from '@/services/api-client';

export function CreateWorkspaceForm({ organizationId }: { organizationId: string }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const createWorkspace = useCreateWorkspace(organizationId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createWorkspace.mutateAsync({ name, slug });
      setName('');
      setSlug('');
      setSlugTouched(false);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create workspace.');
    }
  }

  return (
    <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
      <div className="flex-1 space-y-1">
        <Label htmlFor="workspace-name">Workspace name</Label>
        <Input
          id="workspace-name"
          required
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (!slugTouched) setSlug(slugify(e.target.value));
          }}
        />
      </div>
      <div className="flex-1 space-y-1">
        <Label htmlFor="workspace-slug">Slug</Label>
        <Input
          id="workspace-slug"
          required
          value={slug}
          onChange={(e) => {
            setSlug(e.target.value);
            setSlugTouched(true);
          }}
        />
      </div>
      <Button type="submit" disabled={createWorkspace.isPending}>
        {createWorkspace.isPending ? 'Creating…' : 'Create workspace'}
      </Button>
      {error && (
        <Alert variant="destructive" className="sm:basis-full">
          <AlertTitle>Couldn&apos;t create workspace</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
