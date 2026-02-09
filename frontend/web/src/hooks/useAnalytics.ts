import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import type { FamilyDashboardStats, ChildDashboardStats, AnalyticsResponse } from '../types';

export function useFamilyDashboard(familyId: string) {
  return useQuery({
    queryKey: ['analytics', 'family-dashboard', familyId],
    queryFn: async () => {
      const { data } = await api.get<FamilyDashboardStats>(`/analytics/family/${familyId}/dashboard`);
      return data;
    },
    refetchInterval: 30_000,  // refresh every 30s for real-time feel
  });
}

export function useChildDashboard(childId: string) {
  return useQuery({
    queryKey: ['analytics', 'child-dashboard', childId],
    queryFn: async () => {
      const { data } = await api.get<ChildDashboardStats>(`/analytics/children/${childId}/dashboard`);
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function useChildAnalytics(childId: string, period: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['analytics', 'report', childId, period, startDate, endDate],
    queryFn: async () => {
      const { data } = await api.get<AnalyticsResponse>(`/analytics/children/${childId}/report`, {
        params: { period, start_date: startDate, end_date: endDate },
      });
      return data;
    },
    enabled: !!childId && !!startDate && !!endDate,
  });
}
