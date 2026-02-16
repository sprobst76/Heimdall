import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';
import type { FamilyInvitation, InvitationCreate } from '../types';

export function useInvitations(familyId: string) {
  return useQuery({
    queryKey: ['invitations', familyId],
    queryFn: async () => {
      const { data } = await api.get<FamilyInvitation[]>(`/families/${familyId}/invitations`);
      return data;
    },
    enabled: !!familyId,
  });
}

export function useCreateInvitation(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InvitationCreate) =>
      api.post<FamilyInvitation>(`/families/${familyId}/invitations`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invitations', familyId] }),
  });
}

export function useDeleteInvitation(familyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) =>
      api.delete(`/families/${familyId}/invitations/${invitationId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invitations', familyId] }),
  });
}
