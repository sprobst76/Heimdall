import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';
import {
  BarChart3,
  Clock,
  Trophy,
  Ticket,
  ShieldAlert,
  ArrowLeft,
  Calendar,
  Loader2,
} from 'lucide-react';
import { useChildAnalytics } from '../hooks/useAnalytics';
import type { HeatmapEntry } from '../types';

const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

type Period = 'day' | 'week' | 'month';

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function daysAgo(n: number): Date {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
}

function periodToRange(period: Period): { start: string; end: string } {
  const today = new Date();
  switch (period) {
    case 'day':
      return { start: formatDate(today), end: formatDate(today) };
    case 'week':
      return { start: formatDate(daysAgo(6)), end: formatDate(today) };
    case 'month':
      return { start: formatDate(daysAgo(29)), end: formatDate(today) };
  }
}

const DAY_LABELS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

function heatmapColor(minutes: number, max: number): string {
  if (minutes === 0 || max === 0) return 'bg-slate-100';
  const ratio = minutes / max;
  if (ratio < 0.25) return 'bg-indigo-100';
  if (ratio < 0.5) return 'bg-indigo-300';
  if (ratio < 0.75) return 'bg-indigo-500 text-white';
  return 'bg-indigo-700 text-white';
}

export default function AnalyticsPage() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();

  const [period, setPeriod] = useState<Period>('week');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const range = customStart && customEnd
    ? { start: customStart, end: customEnd }
    : periodToRange(period);

  const { data, isLoading, isError } = useChildAnalytics(
    childId ?? '',
    period,
    range.start,
    range.end,
  );

  // Aggregate summary across all daily summaries
  const summary = useMemo(() => {
    if (!data?.daily_summaries) return null;
    return data.daily_summaries.reduce(
      (acc, d) => ({
        totalMinutes: acc.totalMinutes + d.total_minutes,
        questsCompleted: acc.questsCompleted + d.quests_completed,
        tansRedeemed: acc.tansRedeemed + d.tans_redeemed,
        blockedAttempts: acc.blockedAttempts + d.blocked_attempts,
      }),
      { totalMinutes: 0, questsCompleted: 0, tansRedeemed: 0, blockedAttempts: 0 },
    );
  }, [data]);

  // Build heatmap grid [day][hour]
  const heatmapGrid = useMemo(() => {
    if (!data?.heatmap) return null;
    const grid: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
    let max = 0;
    data.heatmap.forEach((e: HeatmapEntry) => {
      grid[e.day][e.hour] = e.minutes;
      if (e.minutes > max) max = e.minutes;
    });
    return { grid, max };
  }, [data]);

  // Daily usage bar chart data
  const dailyBarData = useMemo(() => {
    if (!data?.daily_summaries) return [];
    return data.daily_summaries.map((d) => ({
      date: d.date.slice(5), // MM-DD
      Minuten: d.total_minutes,
    }));
  }, [data]);

  // Weekly trend line chart data
  const trendData = useMemo(() => {
    if (!data?.trends) return [];
    return data.trends.map((t) => ({
      week: t.week_start.slice(5),
      Minuten: t.total_minutes,
      Quests: t.quests_completed,
      TANs: t.tans_redeemed,
    }));
  }, [data]);

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-4 sm:p-6 lg:p-8">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {data?.child_name ?? 'Analytik'}
          </h1>
          <p className="text-sm text-slate-500">Nutzungsstatistiken &amp; Berichte</p>
        </div>
      </div>

      {/* ── Period selector ─────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {(['day', 'week', 'month'] as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => {
              setPeriod(p);
              setCustomStart('');
              setCustomEnd('');
            }}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              period === p && !customStart
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
            }`}
          >
            {p === 'day' ? 'Tag' : p === 'week' ? 'Woche' : 'Monat'}
          </button>
        ))}
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Calendar className="h-4 w-4" />
          <input
            type="date"
            value={customStart}
            onChange={(e) => setCustomStart(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
          />
          <span>&ndash;</span>
          <input
            type="date"
            value={customEnd}
            onChange={(e) => setCustomEnd(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      {/* ── Loading / empty state ───────────────────────────────── */}
      {isLoading && (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-600">
          Daten konnten nicht geladen werden. Bitte versuche es erneut.
        </div>
      )}

      {!isLoading && !isError && !data && (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-slate-500">
          Noch keine Nutzungsdaten vorhanden. Sobald Aktivitaeten erfasst werden, erscheinen hier die Statistiken.
        </div>
      )}

      {data && summary && (
        <>
          {/* ── Summary cards ─────────────────────────────────────── */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <SummaryCard
              icon={<Clock className="h-5 w-5 text-indigo-500" />}
              label="Gesamtminuten"
              value={summary.totalMinutes}
            />
            <SummaryCard
              icon={<Trophy className="h-5 w-5 text-green-500" />}
              label="Quests erledigt"
              value={summary.questsCompleted}
            />
            <SummaryCard
              icon={<Ticket className="h-5 w-5 text-amber-500" />}
              label="TANs eingeloest"
              value={summary.tansRedeemed}
            />
            <SummaryCard
              icon={<ShieldAlert className="h-5 w-5 text-red-500" />}
              label="Blockierte Versuche"
              value={summary.blockedAttempts}
            />
          </div>

          {/* ── Pie chart: category breakdown ─────────────────────── */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-800">
              <BarChart3 className="h-5 w-5 text-indigo-500" />
              Nutzung nach Kategorie
            </h2>
            {data.group_breakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={data.group_breakdown}
                    dataKey="minutes"
                    nameKey="group_name"
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    label={({ group_name, percentage }) =>
                      `${group_name} (${percentage.toFixed(0)}%)`
                    }
                  >
                    {data.group_breakdown.map((_, idx) => (
                      <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => [`${value} Min.`, 'Minuten']}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-8 text-center text-sm text-slate-400">Keine Kategoriedaten vorhanden.</p>
            )}
          </div>

          {/* ── Bar chart: daily usage ────────────────────────────── */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">
              Taegliche Nutzung
            </h2>
            {dailyBarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dailyBarData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis unit=" Min" tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v: number) => [`${v} Min.`, 'Nutzung']} />
                  <Bar dataKey="Minuten" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-8 text-center text-sm text-slate-400">Keine Tagesdaten vorhanden.</p>
            )}
          </div>

          {/* ── Heatmap: usage by hour / day ──────────────────────── */}
          {heatmapGrid && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">
                Nutzungsmuster (Heatmap)
              </h2>
              <div className="overflow-x-auto">
                <div className="inline-grid gap-1" style={{ gridTemplateColumns: `3rem repeat(24, minmax(1.75rem, 1fr))` }}>
                  {/* Hour headers */}
                  <div />
                  {Array.from({ length: 24 }, (_, h) => (
                    <div key={h} className="text-center text-[10px] text-slate-400">
                      {h}
                    </div>
                  ))}

                  {/* Rows per day */}
                  {DAY_LABELS.map((label, day) => (
                    <>
                      <div key={`label-${day}`} className="flex items-center text-xs font-medium text-slate-500">
                        {label}
                      </div>
                      {heatmapGrid.grid[day].map((minutes, hour) => (
                        <div
                          key={`${day}-${hour}`}
                          title={`${label} ${hour}:00 — ${minutes} Min.`}
                          className={`flex h-7 items-center justify-center rounded text-[10px] font-medium ${heatmapColor(minutes, heatmapGrid.max)}`}
                        >
                          {minutes > 0 ? minutes : ''}
                        </div>
                      ))}
                    </>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Line chart: weekly trends ─────────────────────────── */}
          {trendData.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">
                Woechentliche Trends
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="Minuten" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Quests" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="TANs" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Summary card sub-component ────────────────────────────────────────────── */

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          <p className="text-xs text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  );
}
