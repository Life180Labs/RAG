'use client';

import Link from 'next/link';
import { ChevronRight, Plus } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { CreateOrganizationForm } from '@/components/tenancy/create-organization-form';
import { useOrganizations } from '@/hooks/use-tenancy';

function statusVariant(status: string): 'default' | 'secondary' | 'outline' {
  if (status === 'active') return 'default';
  if (status === 'archived') return 'outline';
  return 'secondary';
}

export function OrganizationList() {
  const { data: organizations, isLoading, isError, error, refetch } = useOrganizations();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="w-full max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-foreground text-xl font-semibold">Organizations</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            Manage your organizations and their workspaces.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreate((v) => !v)} className="gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          New organization
        </Button>
      </div>

      {showCreate && (
        <Card className="border-primary/20 bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Create organization</CardTitle>
          </CardHeader>
          <CardContent>
            <CreateOrganizationForm
              onCreated={() => {
                refetch();
                setShowCreate(false);
              }}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {isLoading && (
            <div className="space-y-px p-1" data-testid="organizations-loading">
              <Skeleton className="h-14 w-full rounded-lg" />
              <Skeleton className="h-14 w-full rounded-lg" />
            </div>
          )}

          {isError && (
            <div className="p-4">
              <Alert variant="destructive">
                <AlertTitle>Couldn&apos;t load organizations</AlertTitle>
                <AlertDescription>
                  {error instanceof Error ? error.message : 'Something went wrong.'}
                </AlertDescription>
              </Alert>
            </div>
          )}

          {organizations && organizations.length === 0 && (
            <div
              className="flex flex-col items-center justify-center py-12 text-center"
              data-testid="organizations-empty"
            >
              <p className="text-foreground text-sm font-medium">No organizations yet</p>
              <p className="text-muted-foreground mt-1 text-xs">
                Create your first organization to get started.
              </p>
              <Button
                size="sm"
                variant="outline"
                className="mt-4 gap-1.5"
                onClick={() => setShowCreate(true)}
              >
                <Plus className="h-3.5 w-3.5" />
                Create organization
              </Button>
            </div>
          )}

          {organizations && organizations.length > 0 && (
            <ul className="divide-border divide-y" data-testid="organizations-list">
              {organizations.map((org) => (
                <li key={org.id}>
                  <Link
                    href={`/organizations/${org.id}`}
                    className="group hover:bg-muted/20 flex items-center justify-between px-5 py-3.5 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-foreground group-hover:text-primary truncate text-sm font-medium transition-colors">
                        {org.name}
                      </p>
                      <p className="text-muted-foreground text-xs">/{org.slug}</p>
                    </div>
                    <div className="ml-4 flex shrink-0 items-center gap-2">
                      <Badge variant={statusVariant(org.status)}>{org.status}</Badge>
                      <ChevronRight className="text-muted-foreground/50 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
