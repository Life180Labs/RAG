'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useCacheStats } from '@/hooks/use-cache';
import type { CacheStats } from '@/types/cache';

const CACHE_TYPE_LABELS: Record<keyof CacheStats, string> = {
  retrieval: 'Retrieval',
  prompt: 'Prompt',
  semantic: 'Semantic',
  metadata: 'Metadata',
};

function hitRatioVariant(ratio: number): 'default' | 'secondary' {
  return ratio > 0 ? 'default' : 'secondary';
}

export function CacheDashboard() {
  const { data, isLoading } = useCacheStats();

  return (
    <Card className="w-full max-w-md" data-testid="cache-dashboard">
      <CardHeader>
        <CardTitle>Cache Hit Ratio</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-2" data-testid="cache-dashboard-loading">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        )}

        {data && (
          <ul className="divide-border divide-y text-sm" data-testid="cache-dashboard-list">
            {(Object.keys(CACHE_TYPE_LABELS) as (keyof CacheStats)[]).map((cacheType) => {
              const stats = data[cacheType];
              return (
                <li
                  key={cacheType}
                  className="flex items-center justify-between gap-2 py-2"
                  data-testid={`cache-dashboard-row-${cacheType}`}
                >
                  <span className="text-muted-foreground">{CACHE_TYPE_LABELS[cacheType]}</span>
                  <span className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">
                      {stats.hits} hits / {stats.misses} misses
                    </span>
                    <Badge variant={hitRatioVariant(stats.hit_ratio)}>
                      {Math.round(stats.hit_ratio * 100)}%
                    </Badge>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
