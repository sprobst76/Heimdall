import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { LoginRequest, PasswordChangeRequest, ProfileUpdate, RegisterRequest, RegisterWithInvitationRequest, TokenResponse, User } from '../types';

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

export function useRegisterWithInvitation() {
  return useMutation({
    mutationFn: async (data: RegisterWithInvitationRequest) => {
      const res = await api.post<TokenResponse>('/auth/register-with-invitation', data);
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

export function useCurrentUser() {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const res = await api.get<User>('/auth/me');
      return res.data;
    },
    enabled: !!localStorage.getItem('access_token'),
    staleTime: 5 * 60 * 1000,
  });
}

export function useFamilyId(): string {
  const { data: user } = useCurrentUser();
  return user?.family_id ?? '';
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: ProfileUpdate) => {
      const res = await api.put<User>('/auth/profile', data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['auth', 'me'] }),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: PasswordChangeRequest) =>
      api.put('/auth/password', data),
  });
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token');
}
