import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { DayTypeOverride, DayTypeOverrideCreate } from '../types';

export function useDayTypes(familyId: string, dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ['day-types', familyId, dateFrom, dateTo],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const qs = params.toString();
      const { data } = await api.get<DayTypeOverride[]>(
        `/families/${familyId}/day-types/${qs ? `?${qs}` : ''}`
      );
      return data;
    },
    enabled: !!familyId,
  });
}

export function useTodayDayType(familyId: string) {
  const today = new Date().toISOString().split('T')[0];
  return useQuery({
    queryKey: ['day-types', 'today', familyId],
    queryFn: async () => {
      const { data } = await api.get<DayTypeOverride[]>(
        `/families/${familyId}/day-types/?date_from=${today}&date_to=${today}`
      );
      return data.length > 0 ? data[0] : null;
    },
    enabled: !!familyId,
  });
}

export function useCreateDayType(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DayTypeOverrideCreate) =>
      api.post<DayTypeOverride>(`/families/${familyId}/day-types/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['day-types'] }),
  });
}

export function useDeleteDayType(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (overrideId: string) =>
      api.delete(`/families/${familyId}/day-types/${overrideId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['day-types'] }),
  });
}

export function useSyncHolidays(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { year: number; subdivision?: string }) =>
      api.post<DayTypeOverride[]>(`/families/${familyId}/day-types/sync-holidays`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['day-types'] }),
  });
}
