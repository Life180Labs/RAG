'use client';

import Link from 'next/link';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateOrganizationForm } from '@/components/tenancy/create-organization-form';
import { useOrganizations } from '@/hooks/use-tenancy';

export function OrganizationList() {
  const { data: organizations, isLoading, isError, error, refetch } = useOrganizations();

  return (
    <div className="w-full max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>New organization</CardTitle>
        </CardHeader>
        <CardContent>
          <CreateOrganizationForm onCreated={() => refetch()} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your organizations</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="space-y-2" data-testid="organizations-loading">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          )}

          {isError && (
            <Alert variant="destructive">
              <AlertTitle>Couldn&apos;t load organizations</AlertTitle>
              <AlertDescription>
                {error instanceof Error ? error.message : 'Something went wrong.'}
              </AlertDescription>
            </Alert>
          )}

          {organizations && organizations.length === 0 && (
            <p className="text-muted-foreground text-sm" data-testid="organizations-empty">
              You don&apos;t belong to any organization yet. Create one above.
            </p>
          )}

          {organizations && organizations.length > 0 && (
            <ul className="divide-border divide-y" data-testid="organizations-list">
              {organizations.map((org) => (
                <li key={org.id} className="flex items-center justify-between py-3">
                  <Link href={`/organizations/${org.id}`} className="font-medium hover:underline">
                    {org.name}
                  </Link>
                  <Badge variant={org.status === 'active' ? 'default' : 'secondary'}>
                    {org.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
