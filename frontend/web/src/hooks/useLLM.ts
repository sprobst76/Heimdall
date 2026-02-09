import { useMutation } from '@tanstack/react-query';
import api from '../api/client';
import type {
  VerifyProofRequest,
  VerifyProofResponse,
  ParseRuleRequest,
  ParseRuleResponse,
  WeeklyReportResponse,
  ChatMessage,
  ChatResponse,
} from '../types';

// ── Proof verification ──────────────────────────────────────────────────────

export function useVerifyProof() {
  return useMutation({
    mutationFn: async (data: VerifyProofRequest) => {
      const { data: result } = await api.post<VerifyProofResponse>(
        '/llm/verify-proof',
        data,
      );
      return result;
    },
  });
}

// ── Natural-language rule parsing ───────────────────────────────────────────

export function useParseRule() {
  return useMutation({
    mutationFn: async (data: ParseRuleRequest) => {
      const { data: result } = await api.post<ParseRuleResponse>(
        '/llm/parse-rule',
        data,
      );
      return result;
    },
  });
}

// ── Weekly report generation ────────────────────────────────────────────────

export function useWeeklyReport() {
  return useMutation({
    mutationFn: async (childId: string) => {
      const { data: result } = await api.post<WeeklyReportResponse>(
        '/llm/weekly-report',
        { child_id: childId },
      );
      return result;
    },
  });
}

// ── Chat ────────────────────────────────────────────────────────────────────

export function useChat() {
  return useMutation({
    mutationFn: async ({
      message,
      history,
    }: {
      message: string;
      history?: ChatMessage[];
    }) => {
      const { data: result } = await api.post<ChatResponse>('/llm/chat', {
        message,
        history,
      });
      return result;
    },
  });
}
