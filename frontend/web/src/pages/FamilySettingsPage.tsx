import { useState } from 'react';
import {
  Users,
  UserPlus,
  Copy,
  Check,
  Trash2,
  Loader2,
  AlertCircle,
  Clock,
  Shield,
} from 'lucide-react';
import { useFamilyId, useCurrentUser } from '../hooks/useAuth';
import { useInvitations, useCreateInvitation, useDeleteInvitation } from '../hooks/useInvitations';
import { useChildren } from '../hooks/useChildren';

function formatExpiry(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = d.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return 'Abgelaufen';
  if (diffDays === 1) return 'Läuft morgen ab';
  return `Noch ${diffDays} Tage gültig`;
}

export default function FamilySettingsPage() {
  const familyId = useFamilyId();
  const { data: currentUser } = useCurrentUser();
  const { data: children } = useChildren(familyId);
  const { data: invitations, isLoading, isError } = useInvitations(familyId);
  const createMutation = useCreateInvitation(familyId);
  const deleteMutation = useDeleteInvitation(familyId);

  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  async function handleCreate() {
    await createMutation.mutateAsync({ role: 'parent' });
  }

  async function handleDelete(id: string) {
    await deleteMutation.mutateAsync(id);
  }

  async function handleCopy(code: string) {
    await navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
          <Users className="h-7 w-7 text-indigo-600" />
          Familie
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Familienmitglieder und Einladungen verwalten
        </p>
      </div>

      {/* Family info */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Übersicht</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500">Eltern</p>
            <p className="mt-1 text-lg font-semibold text-slate-800">
              {currentUser?.name ?? '–'}
            </p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500">Kinder</p>
            <p className="mt-1 text-lg font-semibold text-slate-800">
              {children?.length ?? 0}
            </p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500">Offene Einladungen</p>
            <p className="mt-1 text-lg font-semibold text-slate-800">
              {invitations?.length ?? 0}
            </p>
          </div>
        </div>
      </div>

      {/* Invitations */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Einladungen</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Laden Sie einen weiteren Elternteil ein, Ihrer Familie beizutreten.
            </p>
          </div>
          <button
            onClick={handleCreate}
            disabled={createMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <UserPlus className="h-4 w-4" />
            )}
            Einladung erstellen
          </button>
        </div>

        {isLoading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        )}

        {isError && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            Fehler beim Laden der Einladungen
          </div>
        )}

        {!isLoading && invitations && invitations.length === 0 && (
          <div className="flex flex-col items-center rounded-lg border-2 border-dashed border-slate-200 py-10 text-center">
            <Shield className="mb-3 h-10 w-10 text-slate-300" />
            <p className="text-sm font-medium text-slate-600">Keine offenen Einladungen</p>
            <p className="mt-1 text-xs text-slate-400">
              Erstellen Sie eine Einladung, um einen weiteren Elternteil hinzuzufügen.
            </p>
          </div>
        )}

        {!isLoading && invitations && invitations.length > 0 && (
          <div className="space-y-3">
            {invitations.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-4"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleCopy(inv.code)}
                      className="group flex items-center gap-2 rounded-lg bg-white px-4 py-2 border border-slate-200 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
                      title="Code kopieren"
                    >
                      <span className="font-mono text-lg font-bold tracking-wider text-indigo-600">
                        {inv.code}
                      </span>
                      {copiedCode === inv.code ? (
                        <Check className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <Copy className="h-4 w-4 text-slate-400 group-hover:text-indigo-500" />
                      )}
                    </button>
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatExpiry(inv.expires_at)}
                    </span>
                    <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-600">
                      {inv.role === 'parent' ? 'Elternteil' : inv.role}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(inv.id)}
                  disabled={deleteMutation.isPending}
                  className="ml-3 rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="Einladung widerrufen"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Instructions */}
        <div className="mt-4 rounded-lg bg-indigo-50 p-4">
          <h3 className="text-sm font-medium text-indigo-800">So funktioniert es:</h3>
          <ol className="mt-2 space-y-1 text-xs text-indigo-700">
            <li>1. Erstellen Sie eine Einladung und kopieren Sie den Code.</li>
            <li>2. Teilen Sie den Code mit dem anderen Elternteil.</li>
            <li>3. Der andere Elternteil gibt den Code bei der Registrierung ein.</li>
            <li>4. Beide Elternteile haben Zugriff auf dieselbe Familie.</li>
          </ol>
          <p className="mt-2 text-xs text-indigo-600">
            Einladungen sind 7 Tage gültig und können nur einmal verwendet werden.
          </p>
        </div>
      </div>
    </div>
  );
}
