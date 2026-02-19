import { useState } from 'react';
import { useParams } from 'react-router-dom';
import QRCode from 'react-qr-code';
import { ShieldCheck, ShieldOff, QrCode, Copy, Check, Settings } from 'lucide-react';
import { useTotpStatus, useTotpSetup, useTotpSettings, useTotpDisable } from '../hooks/useTotp';
import type { TotpSetup } from '../types';

const MODE_LABELS: Record<string, string> = {
  tan: 'TAN-Modus (Bonus-Zeit)',
  override: 'Override-Modus (Alle Sperren aufheben)',
  both: 'Beides (Kind wählt beim Einlösen)',
};

export default function TotpPage() {
  const { childId } = useParams<{ childId: string }>();
  const [setupData, setSetupData] = useState<TotpSetup | null>(null);
  const [copied, setCopied] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [mode, setMode] = useState<'tan' | 'override' | 'both'>('tan');
  const [tanMinutes, setTanMinutes] = useState(30);
  const [overrideMinutes, setOverrideMinutes] = useState(30);

  const { data: status, isLoading } = useTotpStatus(childId!);
  const setup = useTotpSetup(childId!);
  const updateSettings = useTotpSettings(childId!);
  const disable = useTotpDisable(childId!);

  const handleSetup = async () => {
    const data = await setup.mutateAsync();
    setSetupData(data);
  };

  const handleCopySecret = () => {
    if (setupData) {
      navigator.clipboard.writeText(setupData.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSaveSettings = () => {
    updateSettings.mutate({ mode, tan_minutes: tanMinutes, override_minutes: overrideMinutes });
    setShowSettings(false);
  };

  const handleDisable = () => {
    if (confirm('TOTP wirklich deaktivieren? Das Kind kann dann keinen Eltern-Code mehr einlösen.')) {
      disable.mutate();
      setSetupData(null);
    }
  };

  if (isLoading) {
    return <div className="p-6 text-slate-500">Lade TOTP-Status...</div>;
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-7 w-7 text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Eltern-Code (TOTP)</h1>
          <p className="text-sm text-slate-500">
            Gibt dem Kind temporären Zugriff per 6-stelligem Code
          </p>
        </div>
      </div>

      {/* Status card */}
      {status && (
        <div className={`rounded-xl border p-5 ${status.enabled ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-white'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {status.enabled ? (
                <ShieldCheck className="h-5 w-5 text-emerald-500" />
              ) : (
                <ShieldOff className="h-5 w-5 text-slate-400" />
              )}
              <span className="font-semibold text-slate-800">
                {status.enabled ? 'TOTP aktiv' : 'TOTP nicht eingerichtet'}
              </span>
            </div>
            {status.enabled && (
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setMode(status.mode);
                    setTanMinutes(status.tan_minutes);
                    setOverrideMinutes(status.override_minutes);
                    setShowSettings(true);
                  }}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
                >
                  <Settings className="h-4 w-4" />
                  Einstellungen
                </button>
                <button
                  onClick={handleDisable}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
                >
                  <ShieldOff className="h-4 w-4" />
                  Deaktivieren
                </button>
              </div>
            )}
          </div>

          {status.enabled && (
            <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-lg bg-white p-3 text-center shadow-sm">
                <div className="text-xs text-slate-500">Modus</div>
                <div className="font-semibold text-slate-800 capitalize">{status.mode}</div>
              </div>
              <div className="rounded-lg bg-white p-3 text-center shadow-sm">
                <div className="text-xs text-slate-500">TAN-Zeit</div>
                <div className="font-semibold text-slate-800">{status.tan_minutes} Min</div>
              </div>
              <div className="rounded-lg bg-white p-3 text-center shadow-sm">
                <div className="text-xs text-slate-500">Override</div>
                <div className="font-semibold text-slate-800">{status.override_minutes} Min</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Setup button */}
      {status && !status.enabled && !setupData && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center">
          <QrCode className="mx-auto mb-3 h-12 w-12 text-slate-300" />
          <p className="mb-4 text-slate-600">
            Richten Sie einen TOTP-Code ein, den der Elternteil in Google Authenticator oder
            einer ähnlichen App speichert. Das Kind kann diesen Code dann eingeben, um
            Bonus-Zeit oder eine Freischaltung zu erhalten.
          </p>
          <button
            onClick={handleSetup}
            disabled={setup.isPending}
            className="rounded-lg bg-indigo-600 px-6 py-2.5 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {setup.isPending ? 'Generiere...' : 'TOTP einrichten'}
          </button>
        </div>
      )}

      {/* QR Code display after setup */}
      {setupData && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-6">
          <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-indigo-900">
            <QrCode className="h-5 w-5" />
            QR-Code scannen
          </h2>
          <p className="mb-5 text-sm text-indigo-700">
            Öffnen Sie Google Authenticator (oder eine kompatible App) und scannen Sie diesen
            QR-Code. Der Code erscheint dann in Ihrer App und wechselt alle 30 Sekunden.
          </p>

          <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
            <div className="rounded-xl bg-white p-4 shadow">
              <QRCode value={setupData.provisioning_uri} size={200} />
            </div>

            <div className="flex-1 space-y-3">
              <div className="rounded-lg bg-white p-4 shadow-sm">
                <div className="mb-1 text-xs text-slate-500">Manueller Schlüssel (falls kein QR-Scan möglich)</div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 break-all text-sm font-mono text-slate-800">
                    {setupData.secret}
                  </code>
                  <button
                    onClick={handleCopySecret}
                    className="flex-shrink-0 rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
                <strong>Wichtig:</strong> Speichern Sie diesen Schlüssel sicher. Nach dem Schließen
                dieses Dialogs ist er nicht mehr sichtbar. Bei Verlust muss TOTP neu eingerichtet
                werden.
              </div>

              <button
                onClick={() => setSetupData(null)}
                className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Fertig — Code gespeichert
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">TOTP-Einstellungen</h2>

            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-700">Modus</label>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value as 'tan' | 'override' | 'both')}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  {Object.entries(MODE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>

              {(mode === 'tan' || mode === 'both') && (
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Bonus-Zeit (TAN-Modus)
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={5}
                      max={480}
                      value={tanMinutes}
                      onChange={(e) => setTanMinutes(Number(e.target.value))}
                      className="w-24 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                    <span className="text-sm text-slate-500">Minuten</span>
                  </div>
                </div>
              )}

              {(mode === 'override' || mode === 'both') && (
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Freigeschaltete Zeit (Override-Modus)
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={5}
                      max={480}
                      value={overrideMinutes}
                      onChange={(e) => setOverrideMinutes(Number(e.target.value))}
                      className="w-24 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                    <span className="text-sm text-slate-500">Minuten</span>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={() => setShowSettings(false)}
                className="flex-1 rounded-lg border border-slate-300 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Abbrechen
              </button>
              <button
                onClick={handleSaveSettings}
                disabled={updateSettings.isPending}
                className="flex-1 rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Speichern
              </button>
            </div>
          </div>
        </div>
      )}

      {/* How it works */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-3 font-semibold text-slate-800">So funktioniert es</h2>
        <ol className="space-y-2 text-sm text-slate-600">
          <li className="flex gap-2">
            <span className="flex-shrink-0 font-bold text-indigo-500">1.</span>
            Elternteil scannt den QR-Code einmalig in Google Authenticator
          </li>
          <li className="flex gap-2">
            <span className="flex-shrink-0 font-bold text-indigo-500">2.</span>
            Die App zeigt alle 30 Sekunden einen neuen 6-stelligen Code
          </li>
          <li className="flex gap-2">
            <span className="flex-shrink-0 font-bold text-indigo-500">3.</span>
            Kind öffnet Heimdall → tippt auf „Eltern-Code" → gibt die 6 Ziffern ein
          </li>
          <li className="flex gap-2">
            <span className="flex-shrink-0 font-bold text-indigo-500">4.</span>
            Bonus-Zeit oder Freischaltung wird sofort aktiv — auch ohne Internet
          </li>
        </ol>
      </div>
    </div>
  );
}
