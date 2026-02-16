import { useState, useMemo } from 'react';
import {
  CalendarDays,
  RefreshCw,
  Trash2,
  Plus,
  Sun,
  Palmtree,
  ChevronLeft,
  ChevronRight,
  X,
  Loader2,
  AlertCircle,
  Info,
} from 'lucide-react';
import { useFamilyId } from '../hooks/useAuth';
import {
  useDayTypes,
  useCreateDayType,
  useDeleteDayType,
  useSyncHolidays,
} from '../hooks/useDayTypes';
import type { DayTypeOverride } from '../types';

// ── Helpers ──────────────────────────────────────────────────────────────────

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

const DAY_TYPE_CONFIG: Record<string, { label: string; bg: string; text: string; border: string; dot: string }> = {
  holiday:  { label: 'Feiertag',      bg: 'bg-red-50',    text: 'text-red-700',    border: 'border-red-200',    dot: 'bg-red-500' },
  vacation: { label: 'Schulferien',   bg: 'bg-sky-50',    text: 'text-sky-700',    border: 'border-sky-200',    dot: 'bg-sky-500' },
  weekend:  { label: 'Wochenende',    bg: 'bg-slate-100', text: 'text-slate-600',  border: 'border-slate-300',  dot: 'bg-slate-400' },
  weekday:  { label: 'Werktag',       bg: 'bg-emerald-50',text: 'text-emerald-700',border: 'border-emerald-200',dot: 'bg-emerald-500' },
};

function dayTypeInfo(type: string) {
  return DAY_TYPE_CONFIG[type] ?? DAY_TYPE_CONFIG.weekday;
}

function formatDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('de-DE', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function getMonthDays(year: number, month: number) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  // Monday-based: 0=Mon ... 6=Sun
  let startOffset = firstDay.getDay() - 1;
  if (startOffset < 0) startOffset = 6;

  const days: (Date | null)[] = [];
  for (let i = 0; i < startOffset; i++) days.push(null);
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push(new Date(year, month, d));
  }
  return days;
}

function toISODate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const MONTH_NAMES = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
];

const DAY_TYPE_OPTIONS = [
  { value: 'holiday', label: 'Feiertag' },
  { value: 'vacation', label: 'Schulferien' },
  { value: 'weekend', label: 'Wochenende' },
  { value: 'weekday', label: 'Werktag' },
];

// ── Component ────────────────────────────────────────────────────────────────

export default function HolidaysPage() {
  const familyId = useFamilyId();
  const now = new Date();
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());

  // Query: load overrides for the displayed month +/- 1 month buffer
  const dateFrom = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-01`;
  const lastDayOfMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const dateTo = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(lastDayOfMonth).padStart(2, '0')}`;

  const { data: overrides, isLoading, isError } = useDayTypes(familyId, dateFrom, dateTo);
  const createMutation = useCreateDayType(familyId);
  const deleteMutation = useDeleteDayType(familyId);
  const syncMutation = useSyncHolidays(familyId);

  // Build lookup: date string → override
  const overrideMap = useMemo(() => {
    const map = new Map<string, DayTypeOverride>();
    overrides?.forEach((o) => map.set(o.date, o));
    return map;
  }, [overrides]);

  // Calendar grid
  const monthDays = useMemo(() => getMonthDays(viewYear, viewMonth), [viewYear, viewMonth]);

  // ── State for modals ──────────────────────────────────────────────────────
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formDate, setFormDate] = useState('');
  const [formDayType, setFormDayType] = useState('holiday');
  const [formLabel, setFormLabel] = useState('');

  // ── Sync state ────────────────────────────────────────────────────────────
  const [syncYear, setSyncYear] = useState(now.getFullYear());
  const [syncResult, setSyncResult] = useState<number | null>(null);

  // ── Navigation ────────────────────────────────────────────────────────────
  function prevMonth() {
    if (viewMonth === 0) {
      setViewYear(viewYear - 1);
      setViewMonth(11);
    } else {
      setViewMonth(viewMonth - 1);
    }
  }

  function nextMonth() {
    if (viewMonth === 11) {
      setViewYear(viewYear + 1);
      setViewMonth(0);
    } else {
      setViewMonth(viewMonth + 1);
    }
  }

  // ── Handlers ──────────────────────────────────────────────────────────────
  function handleDayClick(dateStr: string) {
    const existing = overrideMap.get(dateStr);
    if (existing) {
      setSelectedDay(dateStr);
    } else {
      setFormDate(dateStr);
      setFormDayType('holiday');
      setFormLabel('');
      setShowCreateForm(true);
    }
  }

  async function handleCreate() {
    if (!formDate) return;
    await createMutation.mutateAsync({
      date: formDate,
      day_type: formDayType,
      label: formLabel || undefined,
    });
    setShowCreateForm(false);
  }

  async function handleDelete(overrideId: string) {
    await deleteMutation.mutateAsync(overrideId);
    setSelectedDay(null);
  }

  async function handleSync() {
    const result = await syncMutation.mutateAsync({ year: syncYear, subdivision: 'DE-BW' });
    setSyncResult(result.data.length);
  }

  // ── Today string for highlighting ────────────────────────────────────────
  const todayStr = toISODate(now);

  return (
    <div className="mx-auto max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
          <CalendarDays className="h-7 w-7 text-indigo-600" />
          Ferien- & Feiertagskalender
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Feiertage und Schulferien verwalten. Diese bestimmen, welche Zeitregeln aktiv sind.
        </p>
      </div>

      {/* Sync section */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Feiertage synchronisieren</h2>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={syncYear}
            onChange={(e) => setSyncYear(Number(e.target.value))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value={now.getFullYear()}>{now.getFullYear()}</option>
            <option value={now.getFullYear() + 1}>{now.getFullYear() + 1}</option>
          </select>
          <span className="text-xs text-slate-400">Baden-Württemberg (DE-BW)</span>
          <button
            onClick={handleSync}
            disabled={syncMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Synchronisieren
          </button>
          {syncResult !== null && (
            <span className="text-sm text-emerald-600 font-medium">
              {syncResult} Tage importiert
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Calendar */}
        <div className="lg:col-span-2 rounded-xl border border-slate-200 bg-white p-5">
          {/* Month nav */}
          <div className="mb-4 flex items-center justify-between">
            <button onClick={prevMonth} className="rounded-lg p-2 hover:bg-slate-100">
              <ChevronLeft className="h-5 w-5 text-slate-600" />
            </button>
            <h2 className="text-lg font-semibold text-slate-800">
              {MONTH_NAMES[viewMonth]} {viewYear}
            </h2>
            <button onClick={nextMonth} className="rounded-lg p-2 hover:bg-slate-100">
              <ChevronRight className="h-5 w-5 text-slate-600" />
            </button>
          </div>

          {/* Weekday headers */}
          <div className="mb-1 grid grid-cols-7 gap-1 text-center text-xs font-medium text-slate-400">
            {WEEKDAYS.map((d) => (
              <div key={d} className="py-1">{d}</div>
            ))}
          </div>

          {/* Day cells */}
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-1">
              {monthDays.map((day, i) => {
                if (!day) {
                  return <div key={`empty-${i}`} className="aspect-square" />;
                }

                const dateStr = toISODate(day);
                const override = overrideMap.get(dateStr);
                const isToday = dateStr === todayStr;
                const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                const dtInfo = override ? dayTypeInfo(override.day_type) : null;

                return (
                  <button
                    key={dateStr}
                    onClick={() => handleDayClick(dateStr)}
                    className={`relative aspect-square rounded-lg text-sm font-medium transition-colors ${
                      override
                        ? `${dtInfo!.bg} ${dtInfo!.text} hover:opacity-80`
                        : isWeekend
                          ? 'bg-slate-50 text-slate-400 hover:bg-slate-100'
                          : 'text-slate-700 hover:bg-slate-50'
                    } ${isToday ? 'ring-2 ring-indigo-500 ring-offset-1' : ''}`}
                    title={override ? `${dayTypeInfo(override.day_type).label}: ${override.label ?? ''}` : undefined}
                  >
                    {day.getDate()}
                    {override && (
                      <span className={`absolute bottom-1 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full ${dtInfo!.dot}`} />
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Legend */}
          <div className="mt-4 flex flex-wrap gap-4 border-t border-slate-100 pt-3">
            {Object.entries(DAY_TYPE_CONFIG).map(([key, cfg]) => (
              <div key={key} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className={`h-2.5 w-2.5 rounded-full ${cfg.dot}`} />
                {cfg.label}
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar: Upcoming overrides */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-800">Einträge diesen Monat</h3>
            <button
              onClick={() => {
                setFormDate('');
                setFormDayType('holiday');
                setFormLabel('');
                setShowCreateForm(true);
              }}
              className="flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
            >
              <Plus className="h-3.5 w-3.5" />
              Hinzufügen
            </button>
          </div>

          {isLoading && (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
            </div>
          )}

          {isError && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-xs text-red-600">
              <AlertCircle className="h-4 w-4" />
              Fehler beim Laden
            </div>
          )}

          {!isLoading && overrides && overrides.length === 0 && (
            <div className="flex flex-col items-center py-8 text-center">
              <Info className="mb-2 h-8 w-8 text-slate-300" />
              <p className="text-sm text-slate-500">Keine Einträge in diesem Monat</p>
              <p className="mt-1 text-xs text-slate-400">
                Synchronisieren Sie Feiertage oder fügen Sie manuell hinzu.
              </p>
            </div>
          )}

          {!isLoading && overrides && overrides.length > 0 && (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {overrides.map((o) => {
                const info = dayTypeInfo(o.day_type);
                return (
                  <div
                    key={o.id}
                    className={`flex items-start justify-between rounded-lg border p-3 ${info.border} ${info.bg}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${info.text} ${info.bg}`}>
                          {info.label}
                        </span>
                        <span className="text-xs text-slate-400">
                          {o.source === 'api' ? 'API' : 'Manuell'}
                        </span>
                      </div>
                      <p className="mt-1 text-sm font-medium text-slate-800">
                        {formatDate(o.date)}
                      </p>
                      {o.label && (
                        <p className="mt-0.5 text-xs text-slate-500">{o.label}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleDelete(o.id)}
                      disabled={deleteMutation.isPending}
                      className="ml-2 rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-red-500"
                      title="Löschen"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Create Override Modal ──────────────────────────────────────────── */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">Tagestyp festlegen</h3>
              <button onClick={() => setShowCreateForm(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Datum</label>
                <input
                  type="date"
                  value={formDate}
                  onChange={(e) => setFormDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Tagestyp</label>
                <select
                  value={formDayType}
                  onChange={(e) => setFormDayType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  {DAY_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Bezeichnung <span className="text-slate-400">(optional)</span>
                </label>
                <input
                  type="text"
                  value={formLabel}
                  onChange={(e) => setFormLabel(e.target.value)}
                  placeholder="z.B. Brückentag, Osterferien..."
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateForm(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Abbrechen
              </button>
              <button
                onClick={handleCreate}
                disabled={!formDate || createMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Speichern
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Day Detail Modal ──────────────────────────────────────────────── */}
      {selectedDay && (() => {
        const override = overrideMap.get(selectedDay);
        if (!override) return null;
        const info = dayTypeInfo(override.day_type);

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-900">
                  {formatDate(selectedDay)}
                </h3>
                <button onClick={() => setSelectedDay(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {override.day_type === 'holiday' ? (
                    <Sun className="h-5 w-5 text-red-500" />
                  ) : (
                    <Palmtree className="h-5 w-5 text-sky-500" />
                  )}
                  <span className={`rounded-full px-3 py-1 text-sm font-medium ${info.bg} ${info.text}`}>
                    {info.label}
                  </span>
                </div>

                {override.label && (
                  <p className="text-sm text-slate-700">{override.label}</p>
                )}

                <p className="text-xs text-slate-400">
                  Quelle: {override.source === 'api' ? 'OpenHolidays API' : 'Manuell erstellt'}
                </p>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => setSelectedDay(null)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Schließen
                </button>
                <button
                  onClick={() => handleDelete(override.id)}
                  disabled={deleteMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  <Trash2 className="h-4 w-4" />
                  Löschen
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
