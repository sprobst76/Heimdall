import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type {
  AppGroup,
  AppGroupApp,
  AppGroupCreate,
  AppGroupUpdate,
  AppCreate,
} from '../types';

export function useAppGroups(childId: string) {
  return useQuery({
    queryKey: ['appGroups', childId],
    queryFn: async () => {
      const { data } = await api.get<AppGroup[]>(`/children/${childId}/app-groups`);
      return data;
    },
  });
}

export function useAppGroup(childId: string, groupId: string) {
  return useQuery({
    queryKey: ['appGroups', childId, groupId],
    queryFn: async () => {
      const { data } = await api.get<AppGroup>(
        `/children/${childId}/app-groups/${groupId}`
      );
      return data;
    },
  });
}

export function useCreateAppGroup(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AppGroupCreate) =>
      api.post<AppGroup>(`/children/${childId}/app-groups`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appGroups', childId] }),
  });
}

export function useUpdateAppGroup(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: AppGroupUpdate }) =>
      api.put<AppGroup>(`/children/${childId}/app-groups/${groupId}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appGroups', childId] }),
  });
}

export function useDeleteAppGroup(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (groupId: string) =>
      api.delete(`/children/${childId}/app-groups/${groupId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appGroups', childId] }),
  });
}

export function useAddApp(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: AppCreate }) =>
      api.post<AppGroupApp>(`/children/${childId}/app-groups/${groupId}/apps`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appGroups', childId] }),
  });
}

export function useSetApps(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ groupId, apps }: { groupId: string; apps: AppCreate[] }) =>
      api.put<AppGroupApp[]>(`/children/${childId}/app-groups/${groupId}/apps`, apps),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['appGroups', childId] }),
  });
}
