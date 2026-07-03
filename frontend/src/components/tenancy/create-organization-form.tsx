'use client';

import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateOrganization } from '@/hooks/use-tenancy';
import { slugify } from '@/lib/slug';
import { ApiRequestError } from '@/services/api-client';

export function CreateOrganizationForm({ onCreated }: { onCreated?: () => void }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const createOrganization = useCreateOrganization();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createOrganization.mutateAsync({ name, slug });
      setName('');
      setSlug('');
      setSlugTouched(false);
      onCreated?.();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : 'Unable to create organization.');
    }
  }

  return (
    <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
      <div className="flex-1 space-y-1">
        <Label htmlFor="org-name">Organization name</Label>
        <Input
          id="org-name"
          required
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (!slugTouched) setSlug(slugify(e.target.value));
          }}
        />
      </div>
      <div className="flex-1 space-y-1">
        <Label htmlFor="org-slug">Slug</Label>
        <Input
          id="org-slug"
          required
          value={slug}
          onChange={(e) => {
            setSlug(e.target.value);
            setSlugTouched(true);
          }}
        />
      </div>
      <Button type="submit" disabled={createOrganization.isPending}>
        {createOrganization.isPending ? 'Creating…' : 'Create organization'}
      </Button>
      {error && (
        <Alert variant="destructive" className="sm:basis-full">
          <AlertTitle>Couldn&apos;t create organization</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
