import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { LoginRequest, RegisterRequest, TokenResponse } from '../types';

export function useLogin() {
  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const res = await api.post<TokenResponse>('/auth/login', data);
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      return res.data;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (data: RegisterRequest) => {
      const res = await api.post<TokenResponse>('/auth/register', data);
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      return res.data;
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return () => {
    const refreshToken = localStorage.getItem('refresh_token');
    api.post('/auth/logout', { refresh_token: refreshToken }).catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    queryClient.clear();
    window.location.href = '/login';
  };
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token');
}
