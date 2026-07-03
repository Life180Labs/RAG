'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createContext, useContext, useEffect, useState } from 'react';

import * as authService from '@/services/auth-service';
import { tokenStorage } from '@/lib/token-storage';
import type { User } from '@/types/auth';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    // Bridges browser-only localStorage into React state after mount so the
    // server-rendered pass (no `window`) and the client's first paint match;
    // reading it directly during render would cause a hydration mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHasToken(Boolean(tokenStorage.getAccessToken()));
  }, []);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: ({ signal }) => authService.getMe(signal),
    enabled: hasToken,
    retry: false,
    select: (response) => response.data,
  });

  async function login(email: string, password: string) {
    const response = await authService.login({ email, password });
    tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
    setHasToken(true);
    await refetch();
  }

  async function register(email: string, password: string, fullName: string) {
    await authService.register({ email, password, full_name: fullName });
    await login(email, password);
  }

  async function logout() {
    const refreshToken = tokenStorage.getRefreshToken();
    if (refreshToken) {
      await authService.logout(refreshToken).catch(() => undefined);
    }
    tokenStorage.clear();
    setHasToken(false);
    queryClient.setQueryData(['auth', 'me'], undefined);
  }

  async function refreshUser() {
    await refetch();
  }

  const value: AuthContextValue = {
    user: data ?? null,
    isLoading: hasToken && isLoading,
    isAuthenticated: Boolean(data),
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}
