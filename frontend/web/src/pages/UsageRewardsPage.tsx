import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Gift,
  Plus,
  Loader2,
  AlertCircle,
  X,
  ChevronLeft,
  Pencil,
  Trash2,
  Check,
  Clock,
  TrendingDown,
  Ban,
} from 'lucide-react';
import { useChild } from '../hooks/useChildren';
import {
  useUsageRewards,
  useCreateUsageReward,
  useUpdateUsageReward,
  useDeleteUsageReward,
  useUsageRewardHistory,
} from '../hooks/useUsageRewards';
import { useFamilyId } from '../hooks/useAuth';
import type { UsageRewardRule, UsageRewardRuleCreate } from '../types';

const TRIGGER_OPTIONS = [
  { value: 'daily_under', label: 'Tagesnutzung unter Limit', icon: TrendingDown },
  { value: 'streak_under', label: 'Mehrere Tage unter Limit', icon: Clock },
  { value: 'group_free', label: 'App-Gruppe nicht genutzt', icon: Ban },
];

export default function UsageRewardsPage() {
  const { childId } = useParams<{ childId: string }>();
  const familyId = useFamilyId();
  const { data: child } = useChild(familyId, childId ?? '');
  const { data: rules, isLoading, isError, error } = useUsageRewards(childId ?? '');
  const { data: history } = useUsageRewardHistory(childId ?? '');
  const createRule = useCreateUsageReward(childId ?? '');
  const updateRule = useUpdateUsageReward(childId ?? '');
  const deleteRule = useDeleteUsageReward(childId ?? '');

  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<UsageRewardRule | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'rules' | 'history'>('rules');

  // Form state
  const [formName, setFormName] = useState('');
  const [formTrigger, setFormTrigger] = useState('daily_under');
  const [formThreshold, setFormThreshold] = useState('60');
  const [formStreakDays, setFormStreakDays] = useState('3');
  const [formReward, setFormReward] = useState('15');
  const [formError, setFormError] = useState('');

  function openCreate() {
    setEditingRule(null);
    setFormName('');
    setFormTrigger('daily_under');
    setFormThreshold('60');
    setFormStreakDays('3');
    setFormReward('15');
    setFormError('');
    setShowForm(true);
  }

  function openEdit(rule: UsageRewardRule) {
    setEditingRule(rule);
    setFormName(rule.name);
    setFormTrigger(rule.trigger_type);
    setFormThreshold(String(rule.threshold_minutes));
    setFormStreakDays(String(rule.streak_days ?? 3));
    setFormReward(String(rule.reward_minutes));
    setFormError('');
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingRule(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!formName.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }
    const threshold = parseInt(formThreshold);
    if (!threshold || threshold <= 0) {
      setFormError('Schwellwert muss größer als 0 sein');
      return;
    }
    const reward = parseInt(formReward);
    if (!reward || reward <= 0) {
      setFormError('Belohnung muss größer als 0 sein');
      return;
    }

    try {
      if (editingRule) {
        await updateRule.mutateAsync({
          ruleId: editingRule.id,
          data: {
            name: formName.trim(),
            trigger_type: formTrigger,
            threshold_minutes: threshold,
            streak_days: formTrigger === 'streak_under' ? parseInt(formStreakDays) : null,
            reward_minutes: reward,
          },
        });
      } else {
        const payload: UsageRewardRuleCreate = {
          name: formName.trim(),
          trigger_type: formTrigger,
          threshold_minutes: threshold,
          streak_days: formTrigger === 'streak_under' ? parseInt(formStreakDays) : null,
          reward_minutes: reward,
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

  async function handleDelete(ruleId: string) {
    try {
      await deleteRule.mutateAsync(ruleId);
      setDeleteConfirm(null);
    } catch {
      // Error handled by TanStack Query
    }
  }

  function triggerLabel(type: string) {
    return TRIGGER_OPTIONS.find((t) => t.value === type)?.label ?? type;
  }

  function triggerDescription(rule: UsageRewardRule) {
    if (rule.trigger_type === 'daily_under') {
      return `Unter ${rule.threshold_minutes} Min/Tag → +${rule.reward_minutes} Min`;
    }
    if (rule.trigger_type === 'streak_under') {
      return `${rule.streak_days} Tage unter ${rule.threshold_minutes} Min → +${rule.reward_minutes} Min`;
    }
    if (rule.trigger_type === 'group_free') {
      return `0 Min in Gruppe → +${rule.reward_minutes} Min`;
    }
    return '';
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
            Belohnungen
          </h2>
          {child && (
            <p className="mt-1 text-sm text-slate-500">
              Nutzungsbelohnungen für {child.name}
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

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-slate-100 p-1">
        <button
          onClick={() => setActiveTab('rules')}
          className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            activeTab === 'rules'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Regeln
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            activeTab === 'history'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          Verlauf
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

      {/* Rules Tab */}
      {activeTab === 'rules' && !isLoading && !isError && (
        <>
          {rules && rules.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
              <Gift className="mb-4 h-12 w-12 text-slate-300" />
              <h3 className="text-lg font-semibold text-slate-700">
                Keine Belohnungsregeln
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Erstelle eine Regel, um weniger Bildschirmzeit zu belohnen.
              </p>
            </div>
          )}

          <div className="space-y-3">
            {rules?.map((rule) => (
              <div
                key={rule.id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Gift className="h-5 w-5 text-emerald-500" />
                      <h3 className="text-base font-semibold text-slate-900">
                        {rule.name}
                      </h3>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                      {triggerLabel(rule.trigger_type)}
                    </p>
                    <div className="mt-2 flex items-center gap-4">
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                        <TrendingDown className="h-3 w-3" />
                        {triggerDescription(rule)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openEdit(rule)}
                      className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    {deleteConfirm === rule.id ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDelete(rule.id)}
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
                        onClick={() => setDeleteConfirm(rule.id)}
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
        </>
      )}

      {/* History Tab */}
      {activeTab === 'history' && !isLoading && !isError && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          {(!history || history.length === 0) ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Clock className="mb-3 h-8 w-8 text-slate-300" />
              <p className="text-sm text-slate-500">Noch keine Auswertungen</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-4 py-3 text-left font-medium text-slate-600">Datum</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600">Nutzung</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-600">Limit</th>
                    <th className="px-4 py-3 text-center font-medium text-slate-600">Belohnt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {history.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 text-slate-700">
                        {new Date(log.evaluated_date).toLocaleDateString('de-DE', {
                          weekday: 'short',
                          day: '2-digit',
                          month: '2-digit',
                        })}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-700">
                        {log.usage_minutes} Min
                      </td>
                      <td className="px-4 py-3 text-right text-slate-500">
                        &lt; {log.threshold_minutes} Min
                      </td>
                      <td className="px-4 py-3 text-center">
                        {log.rewarded ? (
                          <Check className="mx-auto h-5 w-5 text-emerald-500" />
                        ) : (
                          <X className="mx-auto h-5 w-5 text-slate-300" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">
                {editingRule ? 'Regel bearbeiten' : 'Neue Belohnungsregel'}
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
                  placeholder="z.B. Wenig-Gaming Bonus"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Trigger Type */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Trigger-Typ
                </label>
                <select
                  value={formTrigger}
                  onChange={(e) => setFormTrigger(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {TRIGGER_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Threshold */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {formTrigger === 'group_free'
                    ? 'Max. erlaubte Minuten (0 = keine Nutzung)'
                    : 'Schwellwert (Minuten)'}
                </label>
                <input
                  type="number"
                  required
                  min={1}
                  value={formThreshold}
                  onChange={(e) => setFormThreshold(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <p className="mt-1 text-xs text-slate-400">
                  {formTrigger === 'daily_under' && 'Bonus wenn Tagesnutzung unter diesem Wert'}
                  {formTrigger === 'streak_under' && 'Bonus wenn mehrere Tage in Folge unter diesem Wert'}
                  {formTrigger === 'group_free' && 'Bonus wenn 0 Minuten in der gewählten App-Gruppe'}
                </p>
              </div>

              {/* Streak Days (only for streak_under) */}
              {formTrigger === 'streak_under' && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Anzahl Tage in Folge
                  </label>
                  <input
                    type="number"
                    required
                    min={2}
                    max={30}
                    value={formStreakDays}
                    onChange={(e) => setFormStreakDays(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                  <p className="mt-1 text-xs text-slate-400">
                    Wie viele Tage in Folge unter dem Limit für die Belohnung
                  </p>
                </div>
              )}

              {/* Reward Minutes */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Belohnung (Bonus-Minuten)
                </label>
                <input
                  type="number"
                  required
                  min={1}
                  max={120}
                  value={formReward}
                  onChange={(e) => setFormReward(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <p className="mt-1 text-xs text-slate-400">
                  Bonus-TAN wird automatisch generiert
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
