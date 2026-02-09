import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Pencil,
  Trash2,
  Shield,
  Ticket,
  Grid3x3,
  Loader2,
  AlertCircle,
  X,
  User as UserIcon,
} from 'lucide-react';
import {
  useChildren,
  useCreateChild,
  useUpdateChild,
  useDeleteChild,
} from '../hooks/useChildren';
import type { User, ChildCreate } from '../types';

const FAMILY_ID = 'demo';

export default function ChildrenPage() {
  const navigate = useNavigate();
  const { data: children, isLoading, isError, error } = useChildren(FAMILY_ID);
  const createChild = useCreateChild(FAMILY_ID);
  const updateChild = useUpdateChild(FAMILY_ID);
  const deleteChild = useDeleteChild(FAMILY_ID);

  const [showForm, setShowForm] = useState(false);
  const [editingChild, setEditingChild] = useState<User | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formAge, setFormAge] = useState('');
  const [formPin, setFormPin] = useState('');
  const [formError, setFormError] = useState('');

  function openCreateForm() {
    setEditingChild(null);
    setFormName('');
    setFormAge('');
    setFormPin('');
    setFormError('');
    setShowForm(true);
  }

  function openEditForm(child: User) {
    setEditingChild(child);
    setFormName(child.name);
    setFormAge(child.age != null ? String(child.age) : '');
    setFormPin('');
    setFormError('');
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingChild(null);
    setFormError('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!formName.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }

    try {
      if (editingChild) {
        await updateChild.mutateAsync({
          childId: editingChild.id,
          data: {
            name: formName.trim(),
            age: formAge ? parseInt(formAge) : null,
          },
        });
      } else {
        const payload: ChildCreate = {
          name: formName.trim(),
          age: formAge ? parseInt(formAge) : null,
          pin: formPin || null,
        };
        await createChild.mutateAsync(payload);
      }
      closeForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Vorgang fehlgeschlagen';
      setFormError(msg);
    }
  }

  async function handleDelete(childId: string) {
    try {
      await deleteChild.mutateAsync(childId);
      setDeleteConfirm(null);
    } catch {
      // Fehler wird ggf. in der Konsole geloggt
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
        <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
        <p className="text-sm font-medium text-red-700">
          Fehler beim Laden: {(error as Error)?.message ?? 'Unbekannter Fehler'}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Kinder</h1>
          <p className="mt-1 text-sm text-slate-500">
            Verwalten Sie die Kinder Ihrer Familie
          </p>
        </div>
        <button
          onClick={openCreateForm}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Kind hinzufugen
        </button>
      </div>

      {/* Empty state */}
      {children && children.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <UserIcon className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Noch keine Kinder angelegt
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Erstellen Sie das erste Profil fur Ihr Kind.
          </p>
        </div>
      )}

      {/* Children list */}
      <div className="space-y-4">
        {children?.map((child) => (
          <div
            key={child.id}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-xl font-bold text-indigo-600">
                  {child.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">
                    {child.name}
                  </h3>
                  <p className="text-sm text-slate-500">
                    {child.age != null ? `${child.age} Jahre` : 'Alter nicht angegeben'}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    Erstellt am{' '}
                    {new Date(child.created_at).toLocaleDateString('de-DE')}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => openEditForm(child)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                  title="Bearbeiten"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setDeleteConfirm(child.id)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="Loschen"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Quick links */}
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => navigate(`/rules/${child.id}`)}
                className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
              >
                <Shield className="h-3.5 w-3.5" />
                Zeitregeln
              </button>
              <button
                onClick={() => navigate(`/tans/${child.id}`)}
                className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
              >
                <Ticket className="h-3.5 w-3.5" />
                TANs
              </button>
              <button
                onClick={() => navigate(`/app-groups/${child.id}`)}
                className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
              >
                <Grid3x3 className="h-3.5 w-3.5" />
                App-Gruppen
              </button>
            </div>

            {/* Delete confirmation */}
            {deleteConfirm === child.id && (
              <div className="mt-4 flex items-center justify-between rounded-lg bg-red-50 px-4 py-3">
                <p className="text-sm text-red-700">
                  Wirklich loschen? Dies kann nicht ruckgangig gemacht werden.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={() => handleDelete(child.id)}
                    disabled={deleteChild.isPending}
                    className="flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    {deleteChild.isPending && (
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
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                {editingChild ? 'Kind bearbeiten' : 'Kind hinzufugen'}
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
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="z.B. Lena"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Alter
                </label>
                <input
                  type="number"
                  min="1"
                  max="18"
                  value={formAge}
                  onChange={(e) => setFormAge(e.target.value)}
                  placeholder="z.B. 10"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {!editingChild && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    PIN (optional)
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={formPin}
                    onChange={(e) =>
                      setFormPin(e.target.value.replace(/\D/g, ''))
                    }
                    placeholder="4-6 stellige PIN"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                  <p className="mt-1 text-xs text-slate-400">
                    PIN fur die Kinder-App (optional)
                  </p>
                </div>
              )}

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
                  disabled={createChild.isPending || updateChild.isPending}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {(createChild.isPending || updateChild.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  {editingChild ? 'Speichern' : 'Erstellen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
