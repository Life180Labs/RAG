'use client';

import { AlertCircle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useHealth } from '@/hooks/use-health';

export function HealthDashboard() {
  const { data, isLoading, isError, error } = useHealth();

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Platform Status</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-2" data-testid="health-loading">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        )}

        {isError && (
          <Alert variant="destructive" data-testid="health-error">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Backend unreachable</AlertTitle>
            <AlertDescription>
              {error instanceof Error ? error.message : 'Unable to reach the API.'}
            </AlertDescription>
          </Alert>
        )}

        {data && (
          <div className="flex items-center justify-between" data-testid="health-success">
            <span className="text-muted-foreground text-sm">API status</span>
            <Badge variant={data.status === 'healthy' ? 'default' : 'destructive'}>
              {data.status} · {data.environment}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
