import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { User, ChildCreate, ChildUpdate } from '../types';

export function useChildren(familyId: string) {
  return useQuery({
    queryKey: ['children', familyId],
    queryFn: async () => {
      const { data } = await api.get<User[]>(`/families/${familyId}/children`);
      return data;
    },
    enabled: !!familyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useChild(familyId: string, childId: string) {
  return useQuery({
    queryKey: ['children', familyId, childId],
    queryFn: async () => {
      const { data } = await api.get<User>(`/families/${familyId}/children/${childId}`);
      return data;
    },
    enabled: !!familyId && !!childId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateChild(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChildCreate) =>
      api.post<User>(`/families/${familyId}/children`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['children', familyId] }),
  });
}

export function useUpdateChild(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ childId, data }: { childId: string; data: ChildUpdate }) =>
      api.put<User>(`/families/${familyId}/children/${childId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['children', familyId] }),
  });
}

export function useDeleteChild(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (childId: string) =>
      api.delete(`/families/${familyId}/children/${childId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['children', familyId] }),
  });
}

export function useResetChildPin(familyId: string) {
  return useMutation({
    mutationFn: ({ childId, pin }: { childId: string; pin: string }) =>
      api.put(`/families/${familyId}/children/${childId}/pin`, { pin }),
  });
}
