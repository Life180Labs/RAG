'use client';

import { AlertCircle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useHealth } from '@/hooks/use-health';
import { cn } from '@/lib/utils';

export function HealthDashboard() {
  const { data, isLoading, isError, error } = useHealth();

  return (
    <Card className="border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          API Status
        </CardTitle>
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
          <div className="flex items-center gap-3" data-testid="health-success">
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                data.status === 'healthy' ? 'bg-green-400' : 'bg-red-400',
              )}
            />
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground capitalize">{data.status}</p>
              <p className="text-xs text-muted-foreground">{data.environment}</p>
            </div>
            <Badge variant={data.status === 'healthy' ? 'default' : 'destructive'} className="text-[0.7rem]">
              {data.status}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
