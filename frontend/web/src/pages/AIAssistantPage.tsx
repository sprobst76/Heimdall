import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Brain,
  Sparkles,
  FileText,
  Wand2,
  Loader2,
  AlertCircle,
  ChevronLeft,
  CheckCircle2,
  Clock,
  Calendar,
  MessageCircle,
  Send,
} from 'lucide-react';
import { useChildren } from '../hooks/useChildren';
import { useCreateRule } from '../hooks/useRules';
import { useParseRule, useWeeklyReport, useChat } from '../hooks/useLLM';
import { useFamilyId } from '../hooks/useAuth';
import type { ChatMessage, ParseRuleResponse, WeeklyReportResponse } from '../types';

const DAY_TYPE_LABELS: Record<string, string> = {
  weekday: 'Wochentag',
  weekend: 'Wochenende',
  holiday: 'Feiertag',
  vacation: 'Ferien',
};

export default function AIAssistantPage() {
  const familyId = useFamilyId();
  const { data: children, isLoading: childrenLoading } = useChildren(familyId);

  // ── NL Rule state ───────────────────────────────────────────────────────
  const [ruleText, setRuleText] = useState('');
  const [ruleChildId, setRuleChildId] = useState('');
  const parseRule = useParseRule();
  const [parsedResult, setParsedResult] = useState<ParseRuleResponse | null>(null);
  const [ruleAdopted, setRuleAdopted] = useState(false);

  // We need createRule for the child that was selected (or the one from parsedResult)
  const adoptChildId = ruleChildId || (parsedResult?.rule?.child_id as string) || '';
  const createRule = useCreateRule(adoptChildId);

  // ── Weekly report state ─────────────────────────────────────────────────
  const [reportChildId, setReportChildId] = useState('');
  const weeklyReport = useWeeklyReport();
  const [report, setReport] = useState<WeeklyReportResponse | null>(null);

  // ── Chat state ────────────────────────────────────────────────────────
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const chat = useChat();
  const chatEndRef = useRef<HTMLDivElement>(null);

  // ── Handlers ────────────────────────────────────────────────────────────

  async function handleParseRule() {
    if (!ruleText.trim()) return;
    setParsedResult(null);
    setRuleAdopted(false);
    try {
      const result = await parseRule.mutateAsync({
        text: ruleText.trim(),
        child_id: ruleChildId || null,
      });
      setParsedResult(result);
    } catch {
      // error is in parseRule.error
    }
  }

  async function handleAdoptRule() {
    if (!parsedResult?.rule) return;
    const r = parsedResult.rule as Record<string, unknown>;
    try {
      await createRule.mutateAsync({
        name: (r.name as string) || 'KI-Regel',
        target_type: (r.target_type as string) || 'device',
        day_types: (r.day_types as string[]) || ['weekday'],
        time_windows: (r.time_windows as Array<{ start: string; end: string }>) || [
          { start: '08:00', end: '20:00' },
        ],
        daily_limit_minutes: (r.daily_limit_minutes as number) ?? null,
        group_limits: (r.group_limits as Array<{ group_id: string; max_minutes: number }>) || [],
        priority: (r.priority as number) || 10,
      });
      setRuleAdopted(true);
    } catch {
      // error is in createRule.error
    }
  }

  async function handleGenerateReport() {
    if (!reportChildId) return;
    setReport(null);
    try {
      const result = await weeklyReport.mutateAsync(reportChildId);
      setReport(result);
    } catch {
      // error is in weeklyReport.error
    }
  }

  async function handleSendChat() {
    const text = chatInput.trim();
    if (!text || chat.isPending) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    const updated = [...chatMessages, userMsg];
    setChatMessages(updated);
    setChatInput('');

    try {
      const result = await chat.mutateAsync({ message: text, history: updated });
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.response },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Entschuldigung, es ist ein Fehler aufgetreten.' },
      ]);
    }

    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  }

  // ── Render helpers ──────────────────────────────────────────────────────

  function renderParsedRule() {
    if (!parsedResult) return null;

    if (!parsedResult.success || !parsedResult.rule) {
      return (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <p className="text-sm font-medium text-red-700">Fehler beim Parsen</p>
          </div>
          {parsedResult.error && (
            <p className="mt-1 text-sm text-red-600">{parsedResult.error}</p>
          )}
        </div>
      );
    }

    const r = parsedResult.rule as {
      name?: string;
      day_types?: string[];
      time_windows?: Array<{ start: string; end: string }>;
      daily_limit_minutes?: number;
      group_limits?: Array<{ group_id: string; max_minutes: number }>;
      explanation?: string;
    };

    return (
      <div className="mt-4 space-y-3">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-5">
          <div className="mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <h4 className="text-sm font-semibold text-emerald-800">
              Erkannte Regel
            </h4>
          </div>

          <div className="space-y-2 text-sm text-slate-700">
            {/* Name */}
            {r.name ? (
              <div className="flex gap-2">
                <span className="font-medium text-slate-500">Name:</span>
                <span>{String(r.name)}</span>
              </div>
            ) : null}

            {/* Day types */}
            {Array.isArray(r.day_types) && (r.day_types as string[]).length > 0 && (
              <div className="flex gap-2">
                <span className="font-medium text-slate-500">Tagestypen:</span>
                <div className="flex flex-wrap gap-1">
                  {(r.day_types as string[]).map((dt) => (
                    <span
                      key={dt}
                      className="flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600"
                    >
                      <Calendar className="h-3 w-3" />
                      {DAY_TYPE_LABELS[dt] || dt}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Time windows */}
            {Array.isArray(r.time_windows) &&
              (r.time_windows as Array<{ start: string; end: string }>).length > 0 && (
                <div className="flex gap-2">
                  <span className="font-medium text-slate-500">Zeitfenster:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {(r.time_windows as Array<{ start: string; end: string }>).map(
                      (tw, i) => (
                        <span
                          key={i}
                          className="flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
                        >
                          <Clock className="h-3 w-3" />
                          {tw.start} - {tw.end}
                        </span>
                      ),
                    )}
                  </div>
                </div>
              )}

            {/* Daily limit */}
            {r.daily_limit_minutes != null && (
              <div className="flex gap-2">
                <span className="font-medium text-slate-500">Tageslimit:</span>
                <span>{r.daily_limit_minutes as number} Minuten</span>
              </div>
            )}

            {/* Group limits */}
            {Array.isArray(r.group_limits) &&
              (r.group_limits as Array<{ group_id: string; max_minutes: number }>)
                .length > 0 && (
                <div className="flex gap-2">
                  <span className="font-medium text-slate-500">Gruppenlimits:</span>
                  <span>
                    {(
                      r.group_limits as Array<{
                        group_id: string;
                        max_minutes: number;
                      }>
                    )
                      .map((gl) => `${gl.group_id}: ${gl.max_minutes} Min.`)
                      .join(', ')}
                  </span>
                </div>
              )}

            {/* Explanation */}
            {r.explanation && (
              <div className="mt-2 rounded-lg bg-white px-3 py-2 text-sm text-slate-600 italic">
                {r.explanation as string}
              </div>
            )}
          </div>

          {/* Adopt button */}
          {!ruleAdopted ? (
            <button
              onClick={handleAdoptRule}
              disabled={createRule.isPending || !adoptChildId}
              className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
            >
              {createRule.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Regel übernehmen
            </button>
          ) : (
            <div className="mt-4 flex items-center gap-2 text-sm font-medium text-emerald-700">
              <CheckCircle2 className="h-4 w-4" />
              Regel wurde erfolgreich erstellt
            </div>
          )}

          {!adoptChildId && !ruleAdopted && (
            <p className="mt-2 text-xs text-amber-600">
              Bitte wählen Sie ein Kind aus, um die Regel zu übernehmen.
            </p>
          )}

          {createRule.isError && (
            <p className="mt-2 text-sm text-red-600">
              Fehler beim Erstellen:{' '}
              {(createRule.error as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail ?? 'Unbekannter Fehler'}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      {/* Back link */}
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-indigo-600"
      >
        <ChevronLeft className="h-4 w-4" />
        Zurück zum Dashboard
      </Link>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
            <Brain className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">KI-Assistent</h1>
            <p className="text-sm text-slate-500">
              Regeln per Sprache erstellen und Wochenberichte generieren
            </p>
          </div>
        </div>
      </div>

      {/* ── Section 1: Natürlichsprachliche Regeln ────────────────────────── */}
      <section className="mb-10">
        <div className="mb-4 flex items-center gap-2">
          <Wand2 className="h-5 w-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-slate-900">
            Natürlichsprachliche Regeln
          </h2>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="mb-4 text-sm text-slate-500">
            Beschreiben Sie eine Regel in normaler Sprache. Die KI erkennt automatisch
            Zeitfenster, Limits und Tagestypen.
          </p>

          {/* Textarea */}
          <textarea
            value={ruleText}
            onChange={(e) => setRuleText(e.target.value)}
            placeholder="z.B. 'Leo darf am Wochenende eine Stunde länger spielen'"
            rows={4}
            className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />

          {/* Child selector + button row */}
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Kind (optional)
              </label>
              <select
                value={ruleChildId}
                onChange={(e) => setRuleChildId(e.target.value)}
                disabled={childrenLoading}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                <option value="">-- Kein Kind ausgewählt --</option>
                {children?.map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.name}
                    {child.age != null ? ` (${child.age} J.)` : ''}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleParseRule}
              disabled={parseRule.isPending || !ruleText.trim()}
              className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
            >
              {parseRule.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )}
              KI-Regel erstellen
            </button>
          </div>

          {/* Parse error (network-level) */}
          {parseRule.isError && !parsedResult && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <p className="text-sm text-red-700">
                  {(parseRule.error as { response?: { data?: { detail?: string } } })
                    ?.response?.data?.detail ?? 'Anfrage fehlgeschlagen'}
                </p>
              </div>
            </div>
          )}

          {/* Parsed result */}
          {renderParsedRule()}
        </div>
      </section>

      {/* ── Section 2: Wochenberichte ─────────────────────────────────────── */}
      <section className="mb-10">
        <div className="mb-4 flex items-center gap-2">
          <FileText className="h-5 w-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-slate-900">Wochenberichte</h2>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="mb-4 text-sm text-slate-500">
            Lassen Sie die KI einen Wochenbericht zur Bildschirmzeit Ihres Kindes erstellen.
          </p>

          {/* Child selector + button */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Kind auswählen
              </label>
              <select
                value={reportChildId}
                onChange={(e) => setReportChildId(e.target.value)}
                disabled={childrenLoading}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                <option value="">-- Kind auswählen --</option>
                {children?.map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.name}
                    {child.age != null ? ` (${child.age} J.)` : ''}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerateReport}
              disabled={weeklyReport.isPending || !reportChildId}
              className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
            >
              {weeklyReport.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Bericht generieren
            </button>
          </div>

          {/* Loading */}
          {weeklyReport.isPending && (
            <div className="mt-6 flex items-center justify-center py-8">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                <p className="text-sm text-slate-500">
                  Bericht wird generiert...
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {weeklyReport.isError && !report && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <p className="text-sm text-red-700">
                  {(
                    weeklyReport.error as {
                      response?: { data?: { detail?: string } };
                    }
                  )?.response?.data?.detail ?? 'Bericht konnte nicht erstellt werden'}
                </p>
              </div>
            </div>
          )}

          {/* Report card */}
          {report && (
            <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-5">
              <div className="mb-3 flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-500" />
                <h3 className="text-base font-semibold text-slate-900">
                  Wochenbericht: {report.child_name}
                </h3>
              </div>
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {report.report}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Section 3: KI-Chat ──────────────────────────────────────────── */}
      <section className="mb-10">
        <div className="mb-4 flex items-center gap-2">
          <MessageCircle className="h-5 w-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-slate-900">KI-Chat</h2>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <p className="border-b border-slate-100 px-6 py-3 text-sm text-slate-500">
            Stellen Sie Fragen zu Bildschirmzeit, Regeln oder Erziehungstipps.
          </p>

          {/* Messages */}
          <div className="h-80 overflow-y-auto px-6 py-4 space-y-3">
            {chatMessages.length === 0 && (
              <p className="py-12 text-center text-sm text-slate-400">
                Noch keine Nachrichten. Stellen Sie eine Frage!
              </p>
            )}
            {chatMessages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-sm'
                      : 'bg-slate-100 text-slate-800 rounded-bl-sm'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {chat.isPending && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-2.5 text-sm text-slate-500 rounded-bl-sm">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Denke nach...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-slate-100 px-4 py-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChat();
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Nachricht eingeben..."
                className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
              <button
                type="submit"
                disabled={chat.isPending || !chatInput.trim()}
                className="flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
