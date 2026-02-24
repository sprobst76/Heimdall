import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { Device } from '../types';

export function useChildDevices(childId: string) {
  return useQuery({
    queryKey: ['devices', childId],
    queryFn: async () => {
      const { data } = await api.get<Device[]>(
        `/children/${childId}/devices/`
      );
      return data;
    },
    enabled: !!childId,
    staleTime: 30_000,
  });
}

export function useBlockAllDevices(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post(`/children/${childId}/devices/block-all`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['devices', childId] }),
  });
}

export function useBlockDevice(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (deviceId: string) =>
      api.post(`/children/${childId}/devices/${deviceId}/block`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['devices', childId] }),
  });
}

export function useUnblockDevice(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (deviceId: string) =>
      api.post(`/children/${childId}/devices/${deviceId}/unblock`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['devices', childId] }),
  });
}
