import { apiGet } from '@/services/api-client';
import type { HealthStatus } from '@/types/api';

export function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  return apiGet<HealthStatus>('/health', signal);
}
