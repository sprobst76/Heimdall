import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { TotpStatus, TotpSetup, TotpSettingsUpdate } from '../types';

export function useTotpStatus(childId: string) {
  return useQuery({
    queryKey: ['totp-status', childId],
    queryFn: async () => {
      const { data } = await api.get<TotpStatus>(`/children/${childId}/totp/status`);
      return data;
    },
    enabled: !!childId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTotpSetup(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<TotpSetup>(`/children/${childId}/totp/setup`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['totp-status', childId] }),
  });
}

export function useTotpSettings(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TotpSettingsUpdate) =>
      api.put<TotpStatus>(`/children/${childId}/totp/settings`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['totp-status', childId] }),
  });
}

export function useTotpDisable(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete(`/children/${childId}/totp`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['totp-status', childId] }),
  });
}
