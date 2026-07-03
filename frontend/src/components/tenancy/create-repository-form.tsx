'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateRepository } from '@/hooks/use-repositories';
import { slugify } from '@/lib/slug';
import { ApiRequestError } from '@/services/api-client';

export function CreateRepositoryForm({ projectId }: { projectId: string }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const createRepository = useCreateRepository(projectId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createRepository.mutateAsync({ name, slug });
      setName('');
      setSlug('');
      setSlugTouched(false);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create repository.');
    }
  }

  return (
    <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
      <div className="flex-1 space-y-1">
        <Label htmlFor="repository-name">Repository name</Label>
        <Input
          id="repository-name"
          required
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (!slugTouched) setSlug(slugify(e.target.value));
          }}
        />
      </div>
      <div className="flex-1 space-y-1">
        <Label htmlFor="repository-slug">Slug</Label>
        <Input
          id="repository-slug"
          required
          value={slug}
          onChange={(e) => {
            setSlug(e.target.value);
            setSlugTouched(true);
          }}
        />
      </div>
      <Button type="submit" disabled={createRepository.isPending}>
        {createRepository.isPending ? 'Creating…' : 'Create repository'}
      </Button>
      {error && (
        <Alert variant="destructive" className="sm:basis-full">
          <AlertTitle>Couldn&apos;t create repository</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
