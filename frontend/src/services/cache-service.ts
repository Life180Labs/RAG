import { apiGet } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { CacheStats } from '@/types/cache';

export const getCacheStats = (signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<CacheStats>>('/cache/stats', signal);
