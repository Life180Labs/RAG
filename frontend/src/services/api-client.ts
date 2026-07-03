import { tokenStorage } from '@/lib/token-storage';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
  /** Attach the stored bearer token. Default true. */
  auth?: boolean;
  /** Internal: set on the retry after a refresh, to prevent refresh loops. */
  skipRefresh?: boolean;
}

// Coalesces concurrent 401s into a single in-flight refresh call instead of
// firing one refresh request per failed request.
let refreshPromise: Promise<void> | null = null;

async function refreshTokens(): Promise<void> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) {
    throw new ApiRequestError('No refresh token available.', 401);
  }

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    tokenStorage.clear();
    throw new ApiRequestError('Session expired.', response.status);
  }

  const body = await response.json();
  tokenStorage.setTokens(body.data.access_token, body.data.refresh_token);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal, auth = true, skipRefresh = false } = options;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (auth) {
    const accessToken = tokenStorage.getAccessToken();
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (response.status === 401 && auth && !skipRefresh && tokenStorage.getRefreshToken()) {
    refreshPromise ??= refreshTokens().finally(() => {
      refreshPromise = null;
    });

    try {
      await refreshPromise;
    } catch {
      throw new ApiRequestError('Session expired.', 401, 'SESSION_EXPIRED');
    }

    return apiRequest<T>(path, { ...options, skipRefresh: true });
  }

  const responseBody = await response.json().catch(() => null);

  if (!response.ok) {
    const code = responseBody?.error?.code;
    const message =
      responseBody?.error?.message ?? `Request to ${path} failed with status ${response.status}`;
    throw new ApiRequestError(message, response.status, code);
  }

  return responseBody as T;
}

export const apiGet = <T>(path: string, signal?: AbortSignal) =>
  apiRequest<T>(path, { method: 'GET', signal });

export const apiPost = <T>(path: string, body?: unknown, options?: Partial<RequestOptions>) =>
  apiRequest<T>(path, { method: 'POST', body, ...options });

export const apiPatch = <T>(path: string, body?: unknown) =>
  apiRequest<T>(path, { method: 'PATCH', body });
