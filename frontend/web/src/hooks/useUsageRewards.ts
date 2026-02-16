import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { UsageRewardRule, UsageRewardRuleCreate, UsageRewardRuleUpdate, UsageRewardLog } from '../types';

export function useUsageRewards(childId: string) {
  return useQuery({
    queryKey: ['usage-rewards', childId],
    queryFn: async () => {
      const { data } = await api.get<UsageRewardRule[]>(`/children/${childId}/usage-rewards/`);
      return data;
    },
    enabled: !!childId,
  });
}

export function useCreateUsageReward(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UsageRewardRuleCreate) =>
      api.post<UsageRewardRule>(`/children/${childId}/usage-rewards/`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['usage-rewards', childId] }),
  });
}

export function useUpdateUsageReward(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: UsageRewardRuleUpdate }) =>
      api.put<UsageRewardRule>(`/children/${childId}/usage-rewards/${ruleId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['usage-rewards', childId] }),
  });
}

export function useDeleteUsageReward(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) =>
      api.delete(`/children/${childId}/usage-rewards/${ruleId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['usage-rewards', childId] }),
  });
}

export function useUsageRewardHistory(childId: string) {
  return useQuery({
    queryKey: ['usage-reward-history', childId],
    queryFn: async () => {
      const { data } = await api.get<UsageRewardLog[]>(`/children/${childId}/usage-rewards/history`);
      return data;
    },
    enabled: !!childId,
  });
}
