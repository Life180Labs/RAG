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

export const apiDelete = <T>(path: string) => apiRequest<T>(path, { method: 'DELETE' });

interface UploadOptions {
  onProgress?: (percent: number) => void;
  signal?: AbortSignal;
  /** Internal: set on the retry after a refresh, to prevent refresh loops. */
  skipRefresh?: boolean;
}

// `apiRequest` always JSON-stringifies its body, which can't carry a File —
// uploads need multipart form data and (for progress events) XMLHttpRequest,
// since fetch has no cross-browser upload-progress signal.
export function apiUpload<T>(path: string, file: File, options: UploadOptions = {}): Promise<T> {
  const { onProgress, signal, skipRefresh = false } = options;

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}${path}`);

    const accessToken = tokenStorage.getAccessToken();
    if (accessToken) xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`);

    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
      };
    }

    if (signal) {
      if (signal.aborted) {
        xhr.abort();
      } else {
        signal.addEventListener('abort', () => xhr.abort());
      }
    }

    xhr.onabort = () => reject(new ApiRequestError('Upload cancelled.', 0, 'UPLOAD_CANCELLED'));
    xhr.onerror = () => reject(new ApiRequestError('Network error during upload.', 0));

    xhr.onload = async () => {
      let responseBody: { data?: T; error?: { code?: string; message?: string } } | null = null;
      try {
        responseBody = JSON.parse(xhr.responseText);
      } catch {
        responseBody = null;
      }

      if (xhr.status === 401 && !skipRefresh && tokenStorage.getRefreshToken()) {
        refreshPromise ??= refreshTokens().finally(() => {
          refreshPromise = null;
        });

        try {
          await refreshPromise;
        } catch {
          reject(new ApiRequestError('Session expired.', 401, 'SESSION_EXPIRED'));
          return;
        }

        try {
          resolve(await apiUpload<T>(path, file, { ...options, skipRefresh: true }));
        } catch (err) {
          reject(err);
        }
        return;
      }

      if (xhr.status < 200 || xhr.status >= 300) {
        const code = responseBody?.error?.code;
        const message =
          responseBody?.error?.message ?? `Request to ${path} failed with status ${xhr.status}`;
        reject(new ApiRequestError(message, xhr.status, code));
        return;
      }

      resolve(responseBody as T);
    };

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  });
}

type DownloadResult =
  { kind: 'redirect'; url: string } | { kind: 'blob'; blob: Blob; filename: string };

// The download endpoint returns *either* a JSON envelope with a presigned
// URL (MinIO backend) *or* the raw file bytes as a stream (local-filesystem
// backend) — see backend/app/api/v1/documents.py. `apiRequest` can't handle
// the latter, so this reads the response directly and branches on
// Content-Type, carrying the same auth/401-refresh handling as other calls.
export async function apiDownload(path: string, skipRefresh = false): Promise<DownloadResult> {
  const accessToken = tokenStorage.getAccessToken();
  const headers: Record<string, string> = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(`${API_BASE_URL}${path}`, { headers });

  if (response.status === 401 && !skipRefresh && tokenStorage.getRefreshToken()) {
    refreshPromise ??= refreshTokens().finally(() => {
      refreshPromise = null;
    });

    try {
      await refreshPromise;
    } catch {
      throw new ApiRequestError('Session expired.', 401, 'SESSION_EXPIRED');
    }

    return apiDownload(path, true);
  }

  const contentType = response.headers.get('content-type') ?? '';

  if (contentType.includes('application/json')) {
    const body = await response.json();
    if (!response.ok) {
      throw new ApiRequestError(
        body?.error?.message ?? `Request to ${path} failed with status ${response.status}`,
        response.status,
        body?.error?.code,
      );
    }
    return { kind: 'redirect', url: body.data.url };
  }

  if (!response.ok) {
    throw new ApiRequestError(
      `Request to ${path} failed with status ${response.status}`,
      response.status,
    );
  }

  const disposition = response.headers.get('content-disposition') ?? '';
  const filename = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? 'download';
  const blob = await response.blob();
  return { kind: 'blob', blob, filename };
}
