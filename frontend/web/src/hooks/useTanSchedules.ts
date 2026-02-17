import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { TanSchedule, TanScheduleCreate, TanScheduleUpdate, TanScheduleLog } from '../types';

export function useTanSchedules(childId: string) {
  return useQuery({
    queryKey: ['tan-schedules', childId],
    queryFn: async () => {
      const { data } = await api.get<TanSchedule[]>(`/children/${childId}/tan-schedules/`);
      return data;
    },
    enabled: !!childId,
  });
}

export function useCreateTanSchedule(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TanScheduleCreate) =>
      api.post<TanSchedule>(`/children/${childId}/tan-schedules/`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tan-schedules', childId] }),
  });
}

export function useUpdateTanSchedule(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ scheduleId, data }: { scheduleId: string; data: TanScheduleUpdate }) =>
      api.put<TanSchedule>(`/children/${childId}/tan-schedules/${scheduleId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tan-schedules', childId] }),
  });
}

export function useDeleteTanSchedule(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scheduleId: string) =>
      api.delete(`/children/${childId}/tan-schedules/${scheduleId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tan-schedules', childId] }),
  });
}

export function useTanScheduleLogs(childId: string, scheduleId: string) {
  return useQuery({
    queryKey: ['tan-schedule-logs', childId, scheduleId],
    queryFn: async () => {
      const { data } = await api.get<TanScheduleLog[]>(
        `/children/${childId}/tan-schedules/${scheduleId}/logs`,
      );
      return data;
    },
    enabled: !!childId && !!scheduleId,
  });
}
