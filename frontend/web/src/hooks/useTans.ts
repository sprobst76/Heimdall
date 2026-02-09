import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { TAN, TANCreate, TANRedeemRequest } from '../types';

export function useTans(childId: string, status?: string) {
  return useQuery({
    queryKey: ['tans', childId, status],
    queryFn: async () => {
      const params = status ? { status } : undefined;
      const { data } = await api.get<TAN[]>(`/children/${childId}/tans`, { params });
      return data;
    },
  });
}

export function useGenerateTan(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TANCreate) =>
      api.post<TAN>(`/children/${childId}/tans/generate`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tans', childId] }),
  });
}

export function useRedeemTan(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TANRedeemRequest) =>
      api.post<TAN>(`/children/${childId}/tans/redeem`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tans', childId] }),
  });
}

export function useDeleteTan(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tanId: string) =>
      api.delete(`/children/${childId}/tans/${tanId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tans', childId] }),
  });
}
