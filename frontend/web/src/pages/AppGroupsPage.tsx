import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Plus,
  Pencil,
  Trash2,
  Loader2,
  AlertCircle,
  X,
  Grid3x3,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  Package,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import {
  useAppGroups,
  useCreateAppGroup,
  useUpdateAppGroup,
  useDeleteAppGroup,
  useAddApp,
} from '../hooks/useAppGroups';
import type { AppGroup, AppGroupCreate, AppCreate } from '../types';

const RISK_LEVELS = [
  { value: 'none', label: 'Kein Risiko', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'low', label: 'Niedrig', color: 'bg-blue-100 text-blue-700' },
  { value: 'medium', label: 'Mittel', color: 'bg-amber-100 text-amber-700' },
  { value: 'high', label: 'Hoch', color: 'bg-red-100 text-red-700' },
];

const CATEGORY_OPTIONS = [
  'Spiele',
  'Soziale Medien',
  'Bildung',
  'Unterhaltung',
  'Kommunikation',
  'Produktivitat',
  'Sonstiges',
];

const PLATFORM_OPTIONS = [
  { value: 'android', label: 'Android' },
  { value: 'windows', label: 'Windows' },
  { value: 'ios', label: 'iOS' },
];

function riskLevelBadge(risk: string) {
  const found = RISK_LEVELS.find((r) => r.value === risk);
  if (!found) return { label: risk, color: 'bg-slate-100 text-slate-600' };
  return found;
}

export default function AppGroupsPage() {
  const { childId } = useParams<{ childId: string }>();
  const { data: groups, isLoading, isError, error } = useAppGroups(childId ?? '');
  const createGroup = useCreateAppGroup(childId ?? '');
  const updateGroup = useUpdateAppGroup(childId ?? '');
  const deleteGroup = useDeleteAppGroup(childId ?? '');
  const addApp = useAddApp(childId ?? '');

  const [showGroupForm, setShowGroupForm] = useState(false);
  const [editingGroup, setEditingGroup] = useState<AppGroup | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [showAppForm, setShowAppForm] = useState<string | null>(null);

  // Group form state
  const [gfName, setGfName] = useState('');
  const [gfIcon, setGfIcon] = useState('');
  const [gfColor, setGfColor] = useState('#4F46E5');
  const [gfCategory, setGfCategory] = useState('Sonstiges');
  const [gfRisk, setGfRisk] = useState('medium');
  const [gfAlwaysAllowed, setGfAlwaysAllowed] = useState(false);
  const [gfTanAllowed, setGfTanAllowed] = useState(true);
  const [gfError, setGfError] = useState('');

  // App form state
  const [afName, setAfName] = useState('');
  const [afPackage, setAfPackage] = useState('');
  const [afExec, setAfExec] = useState('');
  const [afPlatform, setAfPlatform] = useState('android');
  const [afError, setAfError] = useState('');

  function toggleExpanded(id: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function openCreateGroupForm() {
    setEditingGroup(null);
    setGfName('');
    setGfIcon('');
    setGfColor('#4F46E5');
    setGfCategory('Sonstiges');
    setGfRisk('medium');
    setGfAlwaysAllowed(false);
    setGfTanAllowed(true);
    setGfError('');
    setShowGroupForm(true);
  }

  function openEditGroupForm(group: AppGroup) {
    setEditingGroup(group);
    setGfName(group.name);
    setGfIcon(group.icon ?? '');
    setGfColor(group.color ?? '#4F46E5');
    setGfCategory(group.category);
    setGfRisk(group.risk_level);
    setGfAlwaysAllowed(group.always_allowed);
    setGfTanAllowed(group.tan_allowed);
    setGfError('');
    setShowGroupForm(true);
  }

  function closeGroupForm() {
    setShowGroupForm(false);
    setEditingGroup(null);
    setGfError('');
  }

  function openAppForm(groupId: string) {
    setAfName('');
    setAfPackage('');
    setAfExec('');
    setAfPlatform('android');
    setAfError('');
    setShowAppForm(groupId);
  }

  function closeAppForm() {
    setShowAppForm(null);
    setAfError('');
  }

  async function handleGroupSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGfError('');

    if (!gfName.trim()) {
      setGfError('Name ist erforderlich');
      return;
    }

    try {
      if (editingGroup) {
        await updateGroup.mutateAsync({
          groupId: editingGroup.id,
          data: {
            name: gfName.trim(),
            icon: gfIcon || null,
            color: gfColor || null,
            category: gfCategory,
            risk_level: gfRisk,
            always_allowed: gfAlwaysAllowed,
            tan_allowed: gfTanAllowed,
          },
        });
      } else {
        const payload: AppGroupCreate = {
          name: gfName.trim(),
          icon: gfIcon || null,
          color: gfColor || null,
          category: gfCategory,
          risk_level: gfRisk,
          always_allowed: gfAlwaysAllowed,
          tan_allowed: gfTanAllowed,
        };
        await createGroup.mutateAsync(payload);
      }
      closeGroupForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Vorgang fehlgeschlagen';
      setGfError(msg);
    }
  }

  async function handleAppSubmit(e: React.FormEvent, groupId: string) {
    e.preventDefault();
    setAfError('');

    if (!afName.trim()) {
      setAfError('App-Name ist erforderlich');
      return;
    }

    const payload: AppCreate = {
      app_name: afName.trim(),
      app_package: afPackage || null,
      app_executable: afExec || null,
      platform: afPlatform,
    };

    try {
      await addApp.mutateAsync({ groupId, data: payload });
      closeAppForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'App konnte nicht hinzugefugt werden';
      setAfError(msg);
    }
  }

  async function handleDeleteGroup(groupId: string) {
    try {
      await deleteGroup.mutateAsync(groupId);
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
          <h1 className="text-2xl font-bold text-slate-900">App-Gruppen</h1>
          <p className="mt-1 text-sm text-slate-500">
            Kategorien und Apps fur die Bildschirmzeit-Verwaltung
          </p>
        </div>
        <button
          onClick={openCreateGroupForm}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Gruppe erstellen
        </button>
      </div>

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
      {!isLoading && !isError && groups && groups.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <Grid3x3 className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Keine App-Gruppen vorhanden
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Erstellen Sie die erste Gruppe, um Apps zu kategorisieren.
          </p>
        </div>
      )}

      {/* Groups list */}
      <div className="space-y-4">
        {groups?.map((group) => {
          const risk = riskLevelBadge(group.risk_level);
          const isExpanded = expandedGroups.has(group.id);

          return (
            <div
              key={group.id}
              className="rounded-xl border border-slate-200 bg-white shadow-sm"
            >
              {/* Group header */}
              <div className="flex items-start justify-between p-5">
                <div className="flex items-center gap-3">
                  {/* Color indicator */}
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-lg text-white text-sm font-bold"
                    style={{ backgroundColor: group.color ?? '#4F46E5' }}
                  >
                    {group.icon || group.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-semibold text-slate-900">
                        {group.name}
                      </h3>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${risk.color}`}>
                        {risk.label}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                      <span>{group.category}</span>
                      <span>&middot;</span>
                      <span>{group.apps.length} App(s)</span>
                      {group.always_allowed && (
                        <>
                          <span>&middot;</span>
                          <span className="flex items-center gap-0.5 text-emerald-600">
                            <ShieldCheck className="h-3 w-3" />
                            Immer erlaubt
                          </span>
                        </>
                      )}
                      {group.tan_allowed && (
                        <>
                          <span>&middot;</span>
                          <span className="flex items-center gap-0.5 text-indigo-600">
                            <ShieldAlert className="h-3 w-3" />
                            TAN erlaubt
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => toggleExpanded(group.id)}
                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                    title="Apps anzeigen"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </button>
                  <button
                    onClick={() => openEditGroupForm(group)}
                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                    title="Bearbeiten"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(group.id)}
                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500"
                    title="Loschen"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Delete confirmation */}
              {deleteConfirm === group.id && (
                <div className="mx-5 mb-4 flex items-center justify-between rounded-lg bg-red-50 px-4 py-3">
                  <p className="text-sm text-red-700">
                    Gruppe und alle zugehorigen Apps wirklich loschen?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      Abbrechen
                    </button>
                    <button
                      onClick={() => handleDeleteGroup(group.id)}
                      disabled={deleteGroup.isPending}
                      className="flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      {deleteGroup.isPending && (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                      Loschen
                    </button>
                  </div>
                </div>
              )}

              {/* Expanded apps section */}
              {isExpanded && (
                <div className="border-t border-slate-100 px-5 py-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-slate-700">
                      Apps ({group.apps.length})
                    </h4>
                    <button
                      onClick={() => openAppForm(group.id)}
                      className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      <Plus className="h-3 w-3" />
                      App hinzufugen
                    </button>
                  </div>

                  {group.apps.length === 0 ? (
                    <p className="py-4 text-center text-sm text-slate-400">
                      Keine Apps in dieser Gruppe
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {group.apps.map((app) => (
                        <div
                          key={app.id}
                          className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"
                        >
                          <div className="flex items-center gap-2">
                            <Package className="h-4 w-4 text-slate-400" />
                            <div>
                              <p className="text-sm font-medium text-slate-700">
                                {app.app_name}
                              </p>
                              <p className="text-xs text-slate-400">
                                {app.platform}
                                {app.app_package && ` / ${app.app_package}`}
                                {app.app_executable && ` / ${app.app_executable}`}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add app inline form */}
                  {showAppForm === group.id && (
                    <div className="mt-3 rounded-lg border border-slate-200 bg-white p-4">
                      <h5 className="mb-3 text-sm font-semibold text-slate-700">
                        App hinzufugen
                      </h5>
                      {afError && (
                        <div className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
                          {afError}
                        </div>
                      )}
                      <form
                        onSubmit={(e) => handleAppSubmit(e, group.id)}
                        className="space-y-3"
                      >
                        <div>
                          <label className="mb-1 block text-xs font-medium text-slate-600">
                            App-Name *
                          </label>
                          <input
                            type="text"
                            required
                            value={afName}
                            onChange={(e) => setAfName(e.target.value)}
                            placeholder="z.B. YouTube"
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="mb-1 block text-xs font-medium text-slate-600">
                              Paketname
                            </label>
                            <input
                              type="text"
                              value={afPackage}
                              onChange={(e) => setAfPackage(e.target.value)}
                              placeholder="com.google.youtube"
                              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs font-medium text-slate-600">
                              Executable
                            </label>
                            <input
                              type="text"
                              value={afExec}
                              onChange={(e) => setAfExec(e.target.value)}
                              placeholder="youtube.exe"
                              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-slate-600">
                            Plattform
                          </label>
                          <select
                            value={afPlatform}
                            onChange={(e) => setAfPlatform(e.target.value)}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                          >
                            {PLATFORM_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={closeAppForm}
                            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50"
                          >
                            Abbrechen
                          </button>
                          <button
                            type="submit"
                            disabled={addApp.isPending}
                            className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                          >
                            {addApp.isPending && (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            )}
                            Hinzufugen
                          </button>
                        </div>
                      </form>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Create/Edit Group Modal */}
      {showGroupForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                {editingGroup ? 'Gruppe bearbeiten' : 'Gruppe erstellen'}
              </h2>
              <button
                onClick={closeGroupForm}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {gfError && (
              <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                {gfError}
              </div>
            )}

            <form onSubmit={handleGroupSubmit} className="space-y-4">
              {/* Name */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={gfName}
                  onChange={(e) => setGfName(e.target.value)}
                  placeholder="z.B. Spiele"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Icon & Color */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Icon (Emoji / Zeichen)
                  </label>
                  <input
                    type="text"
                    maxLength={4}
                    value={gfIcon}
                    onChange={(e) => setGfIcon(e.target.value)}
                    placeholder="z.B. G"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Farbe
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={gfColor}
                      onChange={(e) => setGfColor(e.target.value)}
                      className="h-10 w-10 cursor-pointer rounded-lg border border-slate-300"
                    />
                    <input
                      type="text"
                      value={gfColor}
                      onChange={(e) => setGfColor(e.target.value)}
                      className="flex-1 rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 font-mono focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>
                </div>
              </div>

              {/* Category */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Kategorie
                </label>
                <select
                  value={gfCategory}
                  onChange={(e) => setGfCategory(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {CATEGORY_OPTIONS.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Risk level */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Risikostufe
                </label>
                <div className="flex flex-wrap gap-2">
                  {RISK_LEVELS.map((rl) => (
                    <button
                      key={rl.value}
                      type="button"
                      onClick={() => setGfRisk(rl.value)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                        gfRisk === rl.value
                          ? rl.color + ' ring-2 ring-offset-1 ring-slate-300'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {rl.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={gfAlwaysAllowed}
                    onChange={(e) => setGfAlwaysAllowed(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/20"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-700">
                      Immer erlaubt
                    </span>
                    <p className="text-xs text-slate-400">
                      Apps in dieser Gruppe werden nicht durch Zeitregeln beschrankt
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={gfTanAllowed}
                    onChange={(e) => setGfTanAllowed(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/20"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-700">
                      TAN-Freischaltung erlaubt
                    </span>
                    <p className="text-xs text-slate-400">
                      Kinder konnen diese Gruppe per TAN freischalten
                    </p>
                  </div>
                </label>
              </div>

              {/* Submit */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeGroupForm}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Abbrechen
                </button>
                <button
                  type="submit"
                  disabled={createGroup.isPending || updateGroup.isPending}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {(createGroup.isPending || updateGroup.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  {editingGroup ? 'Speichern' : 'Erstellen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
