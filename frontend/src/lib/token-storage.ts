// The Phase 1 API returns tokens in the JSON body rather than httpOnly
// cookies, so localStorage is the client-side counterpart of that
// contract. Revisit alongside a cookie-based auth flow if XSS exposure
// becomes a concern for a given deployment.
const ACCESS_TOKEN_KEY = 'rag_access_token';
const REFRESH_TOKEN_KEY = 'rag_refresh_token';

function isBrowser() {
  return typeof window !== 'undefined';
}

export const tokenStorage = {
  getAccessToken(): string | null {
    return isBrowser() ? localStorage.getItem(ACCESS_TOKEN_KEY) : null;
  },
  getRefreshToken(): string | null {
    return isBrowser() ? localStorage.getItem(REFRESH_TOKEN_KEY) : null;
  },
  setTokens(accessToken: string, refreshToken: string): void {
    if (!isBrowser()) return;
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear(): void {
    if (!isBrowser()) return;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
