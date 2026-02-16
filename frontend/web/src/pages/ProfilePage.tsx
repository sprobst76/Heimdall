import { useState } from 'react';
import {
  UserCog,
  Mail,
  Calendar,
  Shield,
  Lock,
  KeyRound,
  Pencil,
  X,
  Check,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useCurrentUser, useUpdateProfile, useChangePassword } from '../hooks/useAuth';
import { useFamilyId } from '../hooks/useAuth';
import { useChildren, useResetChildPin } from '../hooks/useChildren';

function getPasswordStrength(pw: string): 'weak' | 'medium' | 'strong' {
  if (!pw) return 'weak';
  let classes = 0;
  if (/[a-z]/.test(pw)) classes++;
  if (/[A-Z]/.test(pw)) classes++;
  if (/[0-9]/.test(pw)) classes++;
  if (/[^a-zA-Z0-9]/.test(pw)) classes++;

  if (pw.length >= 12 && classes >= 3) return 'strong';
  if (pw.length >= 10 && classes >= 2) return 'medium';
  return 'weak';
}

const STRENGTH_CONFIG = {
  weak: { label: 'Schwach', width: 'w-1/3', color: 'bg-red-500', text: 'text-red-600' },
  medium: { label: 'Mittel', width: 'w-2/3', color: 'bg-amber-500', text: 'text-amber-600' },
  strong: { label: 'Stark', width: 'w-full', color: 'bg-emerald-500', text: 'text-emerald-600' },
};

export default function ProfilePage() {
  const { data: user } = useCurrentUser();
  const familyId = useFamilyId();
  const { data: children } = useChildren(familyId);
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const resetPin = useResetChildPin(familyId);

  // Profile edit state
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');

  // PIN reset state
  const [pinChildId, setPinChildId] = useState<string | null>(null);
  const [pinValue, setPinValue] = useState('');
  const [pinError, setPinError] = useState('');
  const [pinSuccess, setPinSuccess] = useState('');

  function startEditing() {
    setEditName(user?.name ?? '');
    setEditEmail(user?.email ?? '');
    setProfileError('');
    setProfileSuccess('');
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
    setProfileError('');
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    try {
      await updateProfile.mutateAsync({
        name: editName,
        email: editEmail,
      });
      setEditing(false);
      setProfileSuccess('Profil aktualisiert');
      setTimeout(() => setProfileSuccess(''), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Fehler beim Speichern';
      setProfileError(msg);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');

    if (newPassword !== newPasswordConfirm) {
      setPwError('Passwörter stimmen nicht überein');
      return;
    }

    try {
      await changePassword.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });
      setCurrentPassword('');
      setNewPassword('');
      setNewPasswordConfirm('');
      setPwSuccess('Passwort geändert');
      setTimeout(() => setPwSuccess(''), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Fehler beim Ändern';
      setPwError(msg);
    }
  }

  async function handleResetPin(e: React.FormEvent) {
    e.preventDefault();
    if (!pinChildId) return;
    setPinError('');
    setPinSuccess('');

    try {
      await resetPin.mutateAsync({ childId: pinChildId, pin: pinValue });
      setPinChildId(null);
      setPinValue('');
      setPinSuccess('PIN zurückgesetzt');
      setTimeout(() => setPinSuccess(''), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Fehler beim Zurücksetzen';
      setPinError(msg);
    }
  }

  const strength = getPasswordStrength(newPassword);
  const strengthCfg = STRENGTH_CONFIG[strength];

  const createdDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('de-DE', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      })
    : '–';

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
          <UserCog className="h-7 w-7 text-indigo-600" />
          Profil
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Konto-Einstellungen und Kind-PIN-Verwaltung
        </p>
      </div>

      {/* Profile info card */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Profil-Informationen</h2>
          {!editing && (
            <button
              onClick={startEditing}
              className="flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
            >
              <Pencil className="h-3.5 w-3.5" />
              Bearbeiten
            </button>
          )}
        </div>

        {profileSuccess && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
            <Check className="h-4 w-4" />
            {profileSuccess}
          </div>
        )}

        {!editing ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <UserCog className="h-3.5 w-3.5" />
                Name
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-800">{user?.name ?? '–'}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <Mail className="h-3.5 w-3.5" />
                E-Mail
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-800">{user?.email ?? '–'}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <Shield className="h-3.5 w-3.5" />
                Rolle
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-800">
                {user?.role === 'parent' ? 'Elternteil' : user?.role ?? '–'}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <Calendar className="h-3.5 w-3.5" />
                Mitglied seit
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-800">{createdDate}</p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSaveProfile} className="space-y-4">
            {profileError && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                {profileError}
              </div>
            )}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Name</label>
              <input
                type="text"
                required
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">E-Mail</label>
              <input
                type="email"
                required
                value={editEmail}
                onChange={(e) => setEditEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={updateProfile.isPending}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                {updateProfile.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Speichern
              </button>
              <button
                type="button"
                onClick={cancelEditing}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
              >
                Abbrechen
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Password change card */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-800">Passwort ändern</h2>

        {pwSuccess && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
            <Check className="h-4 w-4" />
            {pwSuccess}
          </div>
        )}

        {pwError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            {pwError}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Aktuelles Passwort
            </label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Neues Passwort
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Mindestens 8 Zeichen"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
            {newPassword && (
              <div className="mt-2">
                <div className="h-1.5 w-full rounded-full bg-slate-200">
                  <div className={`h-full rounded-full transition-all ${strengthCfg.width} ${strengthCfg.color}`} />
                </div>
                <p className={`mt-1 text-xs font-medium ${strengthCfg.text}`}>
                  {strengthCfg.label}
                </p>
              </div>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Neues Passwort wiederholen
            </label>
            <input
              type="password"
              required
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 ${
                newPasswordConfirm && newPassword !== newPasswordConfirm
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500/20'
              }`}
            />
            {newPasswordConfirm && newPassword !== newPasswordConfirm && (
              <p className="mt-1 text-xs text-red-600">Passwörter stimmen nicht überein</p>
            )}
          </div>
          <button
            type="submit"
            disabled={changePassword.isPending}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {changePassword.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <Lock className="h-4 w-4" />
            Passwort ändern
          </button>
        </form>
      </div>

      {/* Child PIN management card */}
      {children && children.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold text-slate-800">Kind-PIN verwalten</h2>
          <p className="mb-4 text-xs text-slate-500">
            Setzen Sie einen neuen PIN für die Kind-App-Anmeldung.
          </p>

          {pinSuccess && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
              <Check className="h-4 w-4" />
              {pinSuccess}
            </div>
          )}

          <div className="space-y-3">
            {children.map((child) => (
              <div
                key={child.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600">
                    {child.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800">{child.name}</p>
                    {child.age != null && (
                      <p className="text-xs text-slate-500">{child.age} Jahre</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => {
                    setPinChildId(child.id);
                    setPinValue('');
                    setPinError('');
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
                >
                  <KeyRound className="h-3.5 w-3.5" />
                  PIN zurücksetzen
                </button>
              </div>
            ))}
          </div>

          {/* PIN reset dialog */}
          {pinChildId && (
            <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-indigo-800">
                  Neuen PIN setzen: {children.find((c) => c.id === pinChildId)?.name}
                </h3>
                <button
                  onClick={() => setPinChildId(null)}
                  className="text-indigo-400 hover:text-indigo-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {pinError && (
                <div className="mb-3 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {pinError}
                </div>
              )}

              <form onSubmit={handleResetPin} className="flex gap-2">
                <input
                  type="password"
                  required
                  minLength={4}
                  maxLength={20}
                  value={pinValue}
                  onChange={(e) => setPinValue(e.target.value)}
                  placeholder="Neuer PIN (mind. 4 Zeichen)"
                  className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                <button
                  type="submit"
                  disabled={resetPin.isPending}
                  className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {resetPin.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  Setzen
                </button>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
