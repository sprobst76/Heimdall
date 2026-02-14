import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Plus,
  Pencil,
  Trash2,
  Loader2,
  AlertCircle,
  X,
  Clock,
  ToggleLeft,
  ToggleRight,
  ChevronLeft,
  Calendar,
  Brain,
  ArrowRight,
} from 'lucide-react';
import {
  useRules,
  useCreateRule,
  useUpdateRule,
  useDeleteRule,
} from '../hooks/useRules';
import type { TimeRule, TimeRuleCreate, TimeWindow } from '../types';

const DAY_TYPE_OPTIONS = [
  { value: 'weekday', label: 'Wochentag' },
  { value: 'weekend', label: 'Wochenende' },
  { value: 'holiday', label: 'Feiertag' },
  { value: 'vacation', label: 'Ferien' },
];

const TARGET_TYPE_OPTIONS = [
  { value: 'device', label: 'Gerat' },
  { value: 'app_group', label: 'App-Gruppe' },
];

function formatTimeWindows(windows: TimeWindow[]): string {
  return windows.map((tw) => `${tw.start} - ${tw.end}`).join(', ');
}

function dayTypeLabel(dt: string): string {
  const found = DAY_TYPE_OPTIONS.find((o) => o.value === dt);
  return found ? found.label : dt;
}

export default function RulesPage() {
  const { childId } = useParams<{ childId: string }>();
  const { data: rules, isLoading, isError, error } = useRules(childId ?? '');
  const createRule = useCreateRule(childId ?? '');
  const updateRule = useUpdateRule(childId ?? '');
  const deleteRule = useDeleteRule(childId ?? '');

  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<TimeRule | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formTargetType, setFormTargetType] = useState('device');
  const [formDayTypes, setFormDayTypes] = useState<string[]>(['weekday']);
  const [formWindows, setFormWindows] = useState<TimeWindow[]>([
    { start: '08:00', end: '20:00' },
  ]);
  const [formLimit, setFormLimit] = useState('');
  const [formPriority, setFormPriority] = useState('10');
  const [formError, setFormError] = useState('');

  function openCreateForm() {
    setEditingRule(null);
    setFormName('');
    setFormTargetType('device');
    setFormDayTypes(['weekday']);
    setFormWindows([{ start: '08:00', end: '20:00' }]);
    setFormLimit('');
    setFormPriority('10');
    setFormError('');
    setShowForm(true);
  }

  function openEditForm(rule: TimeRule) {
    setEditingRule(rule);
    setFormName(rule.name);
    setFormTargetType(rule.target_type);
    setFormDayTypes([...rule.day_types]);
    setFormWindows(rule.time_windows.map((tw) => ({ ...tw })));
    setFormLimit(
      rule.daily_limit_minutes != null ? String(rule.daily_limit_minutes) : ''
    );
    setFormPriority(String(rule.priority));
    setFormError('');
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingRule(null);
    setFormError('');
  }

  function toggleDayType(dt: string) {
    setFormDayTypes((prev) =>
      prev.includes(dt) ? prev.filter((d) => d !== dt) : [...prev, dt]
    );
  }

  function addTimeWindow() {
    setFormWindows((prev) => [...prev, { start: '08:00', end: '20:00' }]);
  }

  function removeTimeWindow(idx: number) {
    setFormWindows((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateTimeWindow(idx: number, field: 'start' | 'end', value: string) {
    setFormWindows((prev) =>
      prev.map((tw, i) => (i === idx ? { ...tw, [field]: value } : tw))
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!formName.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }
    if (formDayTypes.length === 0) {
      setFormError('Mindestens ein Tagestyp erforderlich');
      return;
    }
    if (formWindows.length === 0) {
      setFormError('Mindestens ein Zeitfenster erforderlich');
      return;
    }

    try {
      if (editingRule) {
        await updateRule.mutateAsync({
          ruleId: editingRule.id,
          data: {
            name: formName.trim(),
            day_types: formDayTypes,
            time_windows: formWindows,
            daily_limit_minutes: formLimit ? parseInt(formLimit) : null,
            priority: parseInt(formPriority) || 10,
          },
        });
      } else {
        const payload: TimeRuleCreate = {
          name: formName.trim(),
          target_type: formTargetType,
          day_types: formDayTypes,
          time_windows: formWindows,
          daily_limit_minutes: formLimit ? parseInt(formLimit) : null,
          priority: parseInt(formPriority) || 10,
        };
        await createRule.mutateAsync(payload);
      }
      closeForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Vorgang fehlgeschlagen';
      setFormError(msg);
    }
  }

  async function handleToggleActive(rule: TimeRule) {
    await updateRule.mutateAsync({
      ruleId: rule.id,
      data: { active: !rule.active },
    });
  }

  async function handleDelete(ruleId: string) {
    try {
      await deleteRule.mutateAsync(ruleId);
      setDeleteConfirm(null);
    } catch {
      // silent
    }
  }

  if (!childId) {
    return (
      <div className="py-12 text-center text-sm text-slate-500">
        Kein Kind ausgewahlt.
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
        Zuruck zum Dashboard
      </Link>

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Zeitregeln</h1>
          <p className="mt-1 text-sm text-slate-500">
            Bildschirmzeit-Regeln fur dieses Kind verwalten
          </p>
        </div>
        <button
          onClick={openCreateForm}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Regel erstellen
        </button>
      </div>

      {/* KI-Shortcut */}
      <Link
        to="/ai-assistant"
        className="mb-6 flex items-center justify-between rounded-xl border border-indigo-100 bg-indigo-50/50 px-5 py-3.5 transition-colors hover:bg-indigo-50"
      >
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-indigo-500" />
          <div>
            <p className="text-sm font-medium text-slate-800">Regel per KI erstellen</p>
            <p className="text-xs text-slate-500">
              Beschreiben Sie die Regel in normaler Sprache
            </p>
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-indigo-400" />
      </Link>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
          <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
          <p className="text-sm font-medium text-red-700">
            Fehler: {(error as Error)?.message ?? 'Unbekannter Fehler'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && rules && rules.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <Clock className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Keine Regeln vorhanden
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Erstellen Sie die erste Zeitregel fur dieses Kind.
          </p>
        </div>
      )}

      {/* Rules list */}
      <div className="space-y-3">
        {rules?.map((rule) => (
          <div
            key={rule.id}
            className={`rounded-xl border bg-white p-5 shadow-sm transition-all ${
              rule.active
                ? 'border-slate-200'
                : 'border-slate-200 opacity-60'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h3 className="text-base font-semibold text-slate-900">
                    {rule.name}
                  </h3>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      rule.active
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {rule.active ? 'Aktiv' : 'Inaktiv'}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {rule.target_type === 'device' ? 'Gerat' : 'App-Gruppe'}
                  </span>
                </div>

                {/* Day types */}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {rule.day_types.map((dt) => (
                    <span
                      key={dt}
                      className="flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600"
                    >
                      <Calendar className="h-3 w-3" />
                      {dayTypeLabel(dt)}
                    </span>
                  ))}
                </div>

                {/* Time windows */}
                <div className="mt-2 flex items-center gap-1.5 text-sm text-slate-600">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  {formatTimeWindows(rule.time_windows)}
                </div>

                {/* Daily limit */}
                {rule.daily_limit_minutes != null && (
                  <p className="mt-1 text-sm text-slate-500">
                    Tageslimit: {rule.daily_limit_minutes} Minuten
                  </p>
                )}

                {/* Priority */}
                <p className="mt-1 text-xs text-slate-400">
                  Prioritat: {rule.priority}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleToggleActive(rule)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                  title={rule.active ? 'Deaktivieren' : 'Aktivieren'}
                >
                  {rule.active ? (
                    <ToggleRight className="h-5 w-5 text-emerald-500" />
                  ) : (
                    <ToggleLeft className="h-5 w-5" />
                  )}
                </button>
                <button
                  onClick={() => openEditForm(rule)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                  title="Bearbeiten"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setDeleteConfirm(rule.id)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="Loschen"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Delete confirm */}
            {deleteConfirm === rule.id && (
              <div className="mt-4 flex items-center justify-between rounded-lg bg-red-50 px-4 py-3">
                <p className="text-sm text-red-700">Regel wirklich loschen?</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    disabled={deleteRule.isPending}
                    className="flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    {deleteRule.isPending && (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    )}
                    Loschen
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                {editingRule ? 'Regel bearbeiten' : 'Regel erstellen'}
              </h2>
              <button
                onClick={closeForm}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                {formError}
              </div>
            )}

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
                  placeholder="z.B. Schultage Limit"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Target type */}
              {!editingRule && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Zieltyp
                  </label>
                  <select
                    value={formTargetType}
                    onChange={(e) => setFormTargetType(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  >
                    {TARGET_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Day types */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Tagestypen *
                </label>
                <div className="flex flex-wrap gap-2">
                  {DAY_TYPE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleDayType(opt.value)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                        formDayTypes.includes(opt.value)
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time windows */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-sm font-medium text-slate-700">
                    Zeitfenster *
                  </label>
                  <button
                    type="button"
                    onClick={addTimeWindow}
                    className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
                  >
                    <Plus className="h-3 w-3" />
                    Hinzufugen
                  </button>
                </div>
                <div className="space-y-2">
                  {formWindows.map((tw, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="time"
                        value={tw.start}
                        onChange={(e) =>
                          updateTimeWindow(idx, 'start', e.target.value)
                        }
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      />
                      <span className="text-sm text-slate-400">bis</span>
                      <input
                        type="time"
                        value={tw.end}
                        onChange={(e) =>
                          updateTimeWindow(idx, 'end', e.target.value)
                        }
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      />
                      {formWindows.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeTimeWindow(idx)}
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-500"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Daily limit */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Tageslimit (Minuten)
                </label>
                <input
                  type="number"
                  min="1"
                  value={formLimit}
                  onChange={(e) => setFormLimit(e.target.value)}
                  placeholder="z.B. 120"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <p className="mt-1 text-xs text-slate-400">
                  Leer lassen fur kein Limit
                </p>
              </div>

              {/* Priority */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Prioritat
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={formPriority}
                  onChange={(e) => setFormPriority(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <p className="mt-1 text-xs text-slate-400">
                  Hohere Werte haben Vorrang (Standard: 10)
                </p>
              </div>

              {/* Submit */}
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
                  disabled={createRule.isPending || updateRule.isPending}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {(createRule.isPending || updateRule.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  {editingRule ? 'Speichern' : 'Erstellen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
