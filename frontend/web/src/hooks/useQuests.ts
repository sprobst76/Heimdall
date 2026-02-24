import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type {
  QuestTemplate,
  QuestTemplateCreate,
  QuestTemplateUpdate,
  QuestInstance,
  QuestSubmitProof,
  QuestReview,
} from '../types';

// ── Template hooks (family-level) ───────────────────────────────────────────

export function useQuestTemplates(familyId: string) {
  return useQuery({
    queryKey: ['quest-templates', familyId],
    queryFn: async () => {
      const { data } = await api.get<QuestTemplate[]>(
        `/families/${familyId}/quests`
      );
      return data;
    },
    enabled: !!familyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateQuestTemplate(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: QuestTemplateCreate) =>
      api.post<QuestTemplate>(`/families/${familyId}/quests`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quest-templates', familyId] }),
  });
}

export function useUpdateQuestTemplate(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      questId,
      data,
    }: {
      questId: string;
      data: QuestTemplateUpdate;
    }) =>
      api.put<QuestTemplate>(`/families/${familyId}/quests/${questId}`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quest-templates', familyId] }),
  });
}

export function useDeleteQuestTemplate(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (questId: string) =>
      api.delete(`/families/${familyId}/quests/${questId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quest-templates', familyId] }),
  });
}

// ── Instance hooks (child-level) ────────────────────────────────────────────

export function useChildQuests(childId: string, status?: string) {
  return useQuery({
    queryKey: ['quests', childId, status],
    queryFn: async () => {
      const params = status ? { status } : undefined;
      const { data } = await api.get<QuestInstance[]>(
        `/children/${childId}/quests`,
        { params }
      );
      return data;
    },
    enabled: !!childId,
    staleTime: 30_000,
  });
}

export function useAssignQuest(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      api.post<QuestInstance>(
        `/children/${childId}/quests/assign?template_id=${templateId}`
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quests', childId] }),
  });
}

export function useClaimQuest(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (instanceId: string) =>
      api.post<QuestInstance>(
        `/children/${childId}/quests/${instanceId}/claim`
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quests', childId] }),
  });
}

export function useSubmitProof(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      instanceId,
      data,
    }: {
      instanceId: string;
      data: QuestSubmitProof;
    }) =>
      api.post<QuestInstance>(
        `/children/${childId}/quests/${instanceId}/proof`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quests', childId] }),
  });
}

export function useReviewQuest(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      instanceId,
      data,
    }: {
      instanceId: string;
      data: QuestReview;
    }) =>
      api.post<QuestInstance>(
        `/children/${childId}/quests/${instanceId}/review`,
        data
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['quests', childId] }),
  });
}

export function useQuestStats(childId: string) {
  return useQuery({
    queryKey: ['quests', childId, 'stats'],
    queryFn: async () => {
      const { data } = await api.get<Record<string, unknown>>(
        `/children/${childId}/quests/stats`
      );
      return data;
    },
    enabled: !!childId,
    staleTime: 30_000,
  });
}

// ── Upload ──────────────────────────────────────────────────────────────────

export function useUploadProof() {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await api.post<{ url: string }>(
        '/uploads/proof',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      return data;
    },
  });
}
