const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });

  if (!response.ok) {
    throw new ApiRequestError(
      `Request to ${path} failed with status ${response.status}`,
      response.status,
    );
  }

  return response.json() as Promise<T>;
}
