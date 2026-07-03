'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateProject } from '@/hooks/use-tenancy';
import { slugify } from '@/lib/slug';
import { ApiRequestError } from '@/services/api-client';

export function CreateProjectForm({ workspaceId }: { workspaceId: string }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const createProject = useCreateProject(workspaceId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createProject.mutateAsync({ name, slug });
      setName('');
      setSlug('');
      setSlugTouched(false);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create project.');
    }
  }

  return (
    <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
      <div className="flex-1 space-y-1">
        <Label htmlFor="project-name">Project name</Label>
        <Input
          id="project-name"
          required
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (!slugTouched) setSlug(slugify(e.target.value));
          }}
        />
      </div>
      <div className="flex-1 space-y-1">
        <Label htmlFor="project-slug">Slug</Label>
        <Input
          id="project-slug"
          required
          value={slug}
          onChange={(e) => {
            setSlug(e.target.value);
            setSlugTouched(true);
          }}
        />
      </div>
      <Button type="submit" disabled={createProject.isPending}>
        {createProject.isPending ? 'Creating…' : 'Create project'}
      </Button>
      {error && (
        <Alert variant="destructive" className="sm:basis-full">
          <AlertTitle>Couldn&apos;t create project</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
