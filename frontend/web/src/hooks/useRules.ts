import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { TimeRule, TimeRuleCreate, TimeRuleUpdate } from '../types';

export function useRules(childId: string) {
  return useQuery({
    queryKey: ['rules', childId],
    queryFn: async () => {
      const { data } = await api.get<TimeRule[]>(`/children/${childId}/rules`);
      return data;
    },
    enabled: !!childId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRule(childId: string, ruleId: string) {
  return useQuery({
    queryKey: ['rules', childId, ruleId],
    queryFn: async () => {
      const { data } = await api.get<TimeRule>(
        `/children/${childId}/rules/${ruleId}`
      );
      return data;
    },
    enabled: !!childId && !!ruleId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateRule(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TimeRuleCreate) =>
      api.post<TimeRule>(`/children/${childId}/rules`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules', childId] }),
  });
}

export function useUpdateRule(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: TimeRuleUpdate }) =>
      api.put<TimeRule>(`/children/${childId}/rules/${ruleId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules', childId] }),
  });
}

export function useDeleteRule(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) =>
      api.delete(`/children/${childId}/rules/${ruleId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules', childId] }),
  });
}
