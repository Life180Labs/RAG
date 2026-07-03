import { apiGet, apiPatch, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { TokenResponse, User } from '@/types/auth';

export function register(payload: { email: string; password: string; full_name: string }) {
  return apiPost<ApiSuccessResponse<User>>('/auth/register', payload, { auth: false });
}

export function login(payload: { email: string; password: string }) {
  return apiPost<ApiSuccessResponse<TokenResponse>>('/auth/login', payload, { auth: false });
}

export function logout(refreshToken: string) {
  return apiPost<ApiSuccessResponse<{ logged_out: boolean }>>(
    '/auth/logout',
    { refresh_token: refreshToken },
    { auth: false },
  );
}

export function forgotPassword(email: string) {
  return apiPost<ApiSuccessResponse<{ message: string; reset_token?: string }>>(
    '/auth/forgot-password',
    { email },
    { auth: false },
  );
}

export function resetPassword(payload: { reset_token: string; new_password: string }) {
  return apiPost<ApiSuccessResponse<{ reset: boolean }>>('/auth/reset-password', payload, {
    auth: false,
  });
}

export function getMe(signal?: AbortSignal) {
  return apiGet<ApiSuccessResponse<User>>('/users/me', signal);
}

export function updateMe(payload: { full_name: string }) {
  return apiPatch<ApiSuccessResponse<User>>('/users/me', payload);
}
