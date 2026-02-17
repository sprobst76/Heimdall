import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  CalendarClock,
  Plus,
  Loader2,
  AlertCircle,
  X,
  ChevronLeft,
  Pencil,
  Trash2,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';
import { useChild } from '../hooks/useChildren';
import {
  useTanSchedules,
  useCreateTanSchedule,
  useUpdateTanSchedule,
  useDeleteTanSchedule,
} from '../hooks/useTanSchedules';
import { useFamilyId } from '../hooks/useAuth';
import type { TanSchedule, TanScheduleCreate } from '../types';

const RECURRENCE_OPTIONS = [
  { value: 'daily', label: 'Täglich' },
  { value: 'weekdays', label: 'Wochentags (Mo-Fr)' },
  { value: 'weekends', label: 'Wochenende (Sa-So)' },
  { value: 'school_days', label: 'Schultage' },
];

const TAN_TYPE_OPTIONS = [
  { value: 'time', label: 'Zusatzzeit' },
  { value: 'group_unlock', label: 'Gruppe freischalten' },
  { value: 'extend_window', label: 'Zeitfenster erweitern' },
  { value: 'override', label: 'Überschreiben' },
];

function recurrenceLabel(value: string): string {
  return RECURRENCE_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

function tanTypeLabel(value: string): string {
  return TAN_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

function recurrenceColor(value: string): string {
  switch (value) {
    case 'daily':
      return 'bg-blue-50 text-blue-700';
    case 'weekdays':
      return 'bg-emerald-50 text-emerald-700';
    case 'weekends':
      return 'bg-amber-50 text-amber-700';
    case 'school_days':
      return 'bg-violet-50 text-violet-700';
    default:
      return 'bg-slate-50 text-slate-700';
  }
}

export default function TanSchedulesPage() {
  const { childId } = useParams<{ childId: string }>();
  const familyId = useFamilyId();
  const { data: child } = useChild(familyId, childId ?? '');
  const { data: schedules, isLoading, isError, error } = useTanSchedules(childId ?? '');
  const createSchedule = useCreateTanSchedule(childId ?? '');
  const updateSchedule = useUpdateTanSchedule(childId ?? '');
  const deleteSchedule = useDeleteTanSchedule(childId ?? '');

  const [showForm, setShowForm] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<TanSchedule | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formRecurrence, setFormRecurrence] = useState('daily');
  const [formTanType, setFormTanType] = useState('time');
  const [formMinutes, setFormMinutes] = useState('30');
  const [formExpires, setFormExpires] = useState('24');
  const [formError, setFormError] = useState('');

  function openCreate() {
    setEditingSchedule(null);
    setFormName('');
    setFormRecurrence('daily');
    setFormTanType('time');
    setFormMinutes('30');
    setFormExpires('24');
    setFormError('');
    setShowForm(true);
  }

  function openEdit(schedule: TanSchedule) {
    setEditingSchedule(schedule);
    setFormName(schedule.name);
    setFormRecurrence(schedule.recurrence);
    setFormTanType(schedule.tan_type);
    setFormMinutes(String(schedule.value_minutes ?? 30));
    setFormExpires(String(schedule.expires_after_hours));
    setFormError('');
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingSchedule(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!formName.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }
    const minutes = parseInt(formMinutes);
    if (formTanType === 'time' && (!minutes || minutes <= 0)) {
      setFormError('Minuten müssen größer als 0 sein');
      return;
    }
    const expires = parseInt(formExpires);
    if (!expires || expires <= 0) {
      setFormError('Gültigkeitsdauer muss größer als 0 sein');
      return;
    }

    try {
      if (editingSchedule) {
        await updateSchedule.mutateAsync({
          scheduleId: editingSchedule.id,
          data: {
            name: formName.trim(),
            recurrence: formRecurrence,
            tan_type: formTanType,
            value_minutes: formTanType === 'time' ? minutes : null,
            expires_after_hours: expires,
          },
        });
      } else {
        const payload: TanScheduleCreate = {
          name: formName.trim(),
          recurrence: formRecurrence,
          tan_type: formTanType,
          value_minutes: formTanType === 'time' ? minutes : null,
          expires_after_hours: expires,
        };
        await createSchedule.mutateAsync(payload);
      }
      closeForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Vorgang fehlgeschlagen';
      setFormError(msg);
    }
  }

  async function handleDelete(scheduleId: string) {
    try {
      await deleteSchedule.mutateAsync(scheduleId);
      setDeleteConfirm(null);
    } catch {
      // Error handled by TanStack Query
    }
  }

  async function handleToggleActive(schedule: TanSchedule) {
    try {
      await updateSchedule.mutateAsync({
        scheduleId: schedule.id,
        data: { active: !schedule.active },
      });
    } catch {
      // Error handled by TanStack Query
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      {/* Back link */}
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ChevronLeft className="h-4 w-4" />
        Zurück zum Dashboard
      </Link>

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            TAN-Regeln
          </h2>
          {child && (
            <p className="mt-1 text-sm text-slate-500">
              Automatische TAN-Generierung für {child.name}
            </p>
          )}
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Neue Regel
        </button>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
          <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
          <p className="text-sm font-medium text-red-700">
            Fehler: {(error as Error)?.message ?? 'Unbekannter Fehler'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && schedules && schedules.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <CalendarClock className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Keine TAN-Regeln
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Erstelle eine Regel, um TANs automatisch zu generieren.
          </p>
        </div>
      )}

      {/* Schedule list */}
      {!isLoading && !isError && schedules && schedules.length > 0 && (
        <div className="space-y-3">
          {schedules.map((schedule) => (
            <div
              key={schedule.id}
              className={`rounded-xl border bg-white p-5 shadow-sm ${
                schedule.active ? 'border-slate-200' : 'border-slate-100 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <CalendarClock className="h-5 w-5 text-indigo-500" />
                    <h3 className="text-base font-semibold text-slate-900">
                      {schedule.name}
                    </h3>
                    {!schedule.active && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                        Pausiert
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${recurrenceColor(schedule.recurrence)}`}>
                      {recurrenceLabel(schedule.recurrence)}
                    </span>
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                      {tanTypeLabel(schedule.tan_type)}
                    </span>
                    {schedule.value_minutes && (
                      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        +{schedule.value_minutes} Min
                      </span>
                    )}
                    <span className="text-xs text-slate-400">
                      Gültig {schedule.expires_after_hours}h
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleToggleActive(schedule)}
                    className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    title={schedule.active ? 'Pausieren' : 'Aktivieren'}
                  >
                    {schedule.active ? (
                      <ToggleRight className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <ToggleLeft className="h-5 w-5 text-slate-400" />
                    )}
                  </button>
                  <button
                    onClick={() => openEdit(schedule)}
                    className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  {deleteConfirm === schedule.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDelete(schedule.id)}
                        className="rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700"
                      >
                        Löschen
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(null)}
                        className="rounded-md px-2 py-1 text-xs font-medium text-slate-500 hover:text-slate-700"
                      >
                        Abbrechen
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirm(schedule.id)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">
                {editingSchedule ? 'TAN-Regel bearbeiten' : 'Neue TAN-Regel'}
              </h3>
              <button
                onClick={closeForm}
                className="rounded-md p-1 text-slate-400 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="z.B. Wochenend-Gaming-Bonus"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Recurrence */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Wiederholung
                </label>
                <select
                  value={formRecurrence}
                  onChange={(e) => setFormRecurrence(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {RECURRENCE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {formRecurrence === 'school_days' && (
                  <p className="mt-1 text-xs text-slate-400">
                    Mo-Fr ohne Feiertage und Ferien
                  </p>
                )}
              </div>

              {/* TAN Type */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  TAN-Typ
                </label>
                <select
                  value={formTanType}
                  onChange={(e) => setFormTanType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {TAN_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Value Minutes (only for time type) */}
              {formTanType === 'time' && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Bonus-Minuten
                  </label>
                  <input
                    type="number"
                    required
                    min={1}
                    max={120}
                    value={formMinutes}
                    onChange={(e) => setFormMinutes(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                  <p className="mt-1 text-xs text-slate-400">
                    Zusätzliche Bildschirmzeit pro generierter TAN
                  </p>
                </div>
              )}

              {/* Expires */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  TAN gültig für (Stunden)
                </label>
                <input
                  type="number"
                  required
                  min={1}
                  max={168}
                  value={formExpires}
                  onChange={(e) => setFormExpires(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <p className="mt-1 text-xs text-slate-400">
                  Nach dieser Zeit verfällt die generierte TAN automatisch
                </p>
              </div>

              {/* Error */}
              {formError && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {formError}
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeForm}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Abbrechen
                </button>
                <button
                  type="submit"
                  disabled={createSchedule.isPending || updateSchedule.isPending}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {(createSchedule.isPending || updateSchedule.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  {editingSchedule ? 'Speichern' : 'Erstellen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
