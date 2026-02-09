import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  X,
  Ticket,
  Copy,
  Check,
  ChevronLeft,
  Clock,
} from 'lucide-react';
import { useTans, useGenerateTan, useDeleteTan } from '../hooks/useTans';
import type { TAN, TANCreate } from '../types';

const TAN_TYPE_OPTIONS = [
  { value: 'time', label: 'Zusatzzeit' },
  { value: 'group_unlock', label: 'Gruppe freischalten' },
  { value: 'extend_window', label: 'Zeitfenster erweitern' },
  { value: 'override', label: 'Uberschreiben' },
];

function statusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'bg-emerald-100 text-emerald-700';
    case 'redeemed':
      return 'bg-slate-100 text-slate-500';
    case 'expired':
      return 'bg-red-100 text-red-600';
    default:
      return 'bg-slate-100 text-slate-500';
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'active':
      return 'Aktiv';
    case 'redeemed':
      return 'Eingelost';
    case 'expired':
      return 'Abgelaufen';
    default:
      return status;
  }
}

function typeLabel(type: string): string {
  const found = TAN_TYPE_OPTIONS.find((o) => o.value === type);
  return found ? found.label : type;
}

export default function TansPage() {
  const { childId } = useParams<{ childId: string }>();
  const { data: tans, isLoading, isError, error } = useTans(childId ?? '');
  const generateTan = useGenerateTan(childId ?? '');
  const deleteTan = useDeleteTan(childId ?? '');

  const [showForm, setShowForm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [generatedTan, setGeneratedTan] = useState<TAN | null>(null);

  // Form state
  const [formType, setFormType] = useState('time');
  const [formMinutes, setFormMinutes] = useState('30');
  const [formUnlockUntil, setFormUnlockUntil] = useState('');
  const [formExpiry, setFormExpiry] = useState('');
  const [formSingleUse, setFormSingleUse] = useState(true);
  const [formError, setFormError] = useState('');

  function openForm() {
    setFormType('time');
    setFormMinutes('30');
    setFormUnlockUntil('');
    setFormExpiry('');
    setFormSingleUse(true);
    setFormError('');
    setGeneratedTan(null);
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setGeneratedTan(null);
    setFormError('');
  }

  async function handleCopy(code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch {
      // Fallback: select text (handled by user)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    const payload: TANCreate = {
      type: formType,
      single_use: formSingleUse,
    };

    if (formType === 'time' || formType === 'extend_window') {
      const mins = parseInt(formMinutes);
      if (!mins || mins <= 0) {
        setFormError('Bitte geben Sie eine gultige Minutenzahl ein');
        return;
      }
      payload.value_minutes = mins;
    }

    if (formType === 'group_unlock' && formUnlockUntil) {
      payload.value_unlock_until = formUnlockUntil;
    }

    if (formExpiry) {
      payload.expires_at = new Date(formExpiry).toISOString();
    }

    try {
      const result = await generateTan.mutateAsync(payload);
      setGeneratedTan(result.data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'TAN-Erstellung fehlgeschlagen';
      setFormError(msg);
    }
  }

  async function handleDelete(tanId: string) {
    try {
      await deleteTan.mutateAsync(tanId);
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
          <h1 className="text-2xl font-bold text-slate-900">TANs</h1>
          <p className="mt-1 text-sm text-slate-500">
            TAN-Codes fur Bonuszeit oder Freischaltungen verwalten
          </p>
        </div>
        <button
          onClick={openForm}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          TAN generieren
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
      {!isLoading && !isError && tans && tans.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <Ticket className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Keine TANs vorhanden
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Generieren Sie den ersten TAN-Code.
          </p>
        </div>
      )}

      {/* TANs list */}
      <div className="space-y-3">
        {tans?.map((tan) => (
          <div
            key={tan.id}
            className={`rounded-xl border bg-white p-5 shadow-sm ${
              tan.status === 'active' ? 'border-slate-200' : 'border-slate-200 opacity-70'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  {/* TAN code */}
                  <div className="flex items-center gap-2">
                    <code className="rounded-lg bg-slate-900 px-3 py-1.5 font-mono text-lg font-bold tracking-wider text-white">
                      {tan.code}
                    </code>
                    <button
                      onClick={() => handleCopy(tan.code)}
                      className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                      title="Code kopieren"
                    >
                      {copiedCode === tan.code ? (
                        <Check className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>

                  {/* Status badge */}
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(
                      tan.status
                    )}`}
                  >
                    {statusLabel(tan.status)}
                  </span>
                </div>

                {/* Details */}
                <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
                  <span className="flex items-center gap-1">
                    <Ticket className="h-3.5 w-3.5 text-slate-400" />
                    {typeLabel(tan.type)}
                  </span>
                  {tan.value_minutes != null && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      {tan.value_minutes} Min.
                    </span>
                  )}
                  {tan.value_unlock_until && (
                    <span>Bis {tan.value_unlock_until}</span>
                  )}
                  <span className="text-xs text-slate-400">
                    Ablauf:{' '}
                    {new Date(tan.expires_at).toLocaleString('de-DE', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </span>
                </div>

                {/* Metadata */}
                <div className="mt-1 flex gap-3 text-xs text-slate-400">
                  {tan.single_use && <span>Einmalig</span>}
                  {tan.source && <span>Quelle: {tan.source}</span>}
                  {tan.redeemed_at && (
                    <span>
                      Eingelost:{' '}
                      {new Date(tan.redeemed_at).toLocaleString('de-DE', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      })}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              {tan.status === 'active' && (
                <button
                  onClick={() => setDeleteConfirm(tan.id)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="Invalidieren"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Delete confirm */}
            {deleteConfirm === tan.id && (
              <div className="mt-4 flex items-center justify-between rounded-lg bg-red-50 px-4 py-3">
                <p className="text-sm text-red-700">
                  TAN wirklich invalidieren?
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                  >
                    Abbrechen
                  </button>
                  <button
                    onClick={() => handleDelete(tan.id)}
                    disabled={deleteTan.isPending}
                    className="flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    {deleteTan.isPending && (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    )}
                    Invalidieren
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Generate TAN Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                TAN generieren
              </h2>
              <button
                onClick={closeForm}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Show generated TAN */}
            {generatedTan && (
              <div className="mb-6">
                <div className="flex flex-col items-center rounded-xl bg-emerald-50 p-6">
                  <p className="mb-2 text-sm font-medium text-emerald-700">
                    TAN erfolgreich erstellt!
                  </p>
                  <div className="flex items-center gap-3">
                    <code className="rounded-xl bg-slate-900 px-6 py-3 font-mono text-3xl font-bold tracking-widest text-white">
                      {generatedTan.code}
                    </code>
                    <button
                      onClick={() => handleCopy(generatedTan.code)}
                      className="rounded-lg bg-white p-3 text-slate-500 shadow-sm transition-colors hover:text-slate-700"
                      title="Kopieren"
                    >
                      {copiedCode === generatedTan.code ? (
                        <Check className="h-5 w-5 text-emerald-500" />
                      ) : (
                        <Copy className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                  <p className="mt-3 text-xs text-emerald-600">
                    Gultig bis:{' '}
                    {new Date(generatedTan.expires_at).toLocaleString('de-DE', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })}
                  </p>
                </div>

                <div className="mt-4 flex gap-3">
                  <button
                    onClick={closeForm}
                    className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  >
                    Schliessen
                  </button>
                  <button
                    onClick={() => {
                      setGeneratedTan(null);
                      setFormError('');
                    }}
                    className="flex-1 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
                  >
                    Weitere TAN erstellen
                  </button>
                </div>
              </div>
            )}

            {/* Form */}
            {!generatedTan && (
              <>
                {formError && (
                  <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                    {formError}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Type */}
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      Typ
                    </label>
                    <select
                      value={formType}
                      onChange={(e) => setFormType(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    >
                      {TAN_TYPE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Minutes (for time / extend_window) */}
                  {(formType === 'time' || formType === 'extend_window') && (
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        Minuten
                      </label>
                      <input
                        type="number"
                        min="5"
                        step="5"
                        required
                        value={formMinutes}
                        onChange={(e) => setFormMinutes(e.target.value)}
                        placeholder="z.B. 30"
                        className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                  )}

                  {/* Unlock until (for group_unlock) */}
                  {formType === 'group_unlock' && (
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        Freischalten bis (Uhrzeit)
                      </label>
                      <input
                        type="time"
                        value={formUnlockUntil}
                        onChange={(e) => setFormUnlockUntil(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                  )}

                  {/* Expiry */}
                  <div>
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      Ablaufdatum (optional)
                    </label>
                    <input
                      type="datetime-local"
                      value={formExpiry}
                      onChange={(e) => setFormExpiry(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    />
                    <p className="mt-1 text-xs text-slate-400">
                      Standard: Ende des heutigen Tages
                    </p>
                  </div>

                  {/* Single use */}
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formSingleUse}
                      onChange={(e) => setFormSingleUse(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/20"
                    />
                    <span className="text-sm text-slate-700">
                      Einmalige Verwendung
                    </span>
                  </label>

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
                      disabled={generateTan.isPending}
                      className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {generateTan.isPending && (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      )}
                      TAN generieren
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
