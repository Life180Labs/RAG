import { useQuery } from '@tanstack/react-query';

import { getCacheStats } from '@/services/cache-service';

export function useCacheStats() {
  return useQuery({
    queryKey: ['cache', 'stats'],
    queryFn: ({ signal }) => getCacheStats(signal),
    select: (response) => response.data,
    refetchInterval: 15_000,
  });
}
