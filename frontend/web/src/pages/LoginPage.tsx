import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useLogin, useRegister, useRegisterWithInvitation } from '../hooks/useAuth';

type Tab = 'login' | 'register';

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

export default function LoginPage() {
  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [name, setName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [invitationCode, setInvitationCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const navigate = useNavigate();
  const login = useLogin();
  const register = useRegister();
  const registerWithInvitation = useRegisterWithInvitation();

  const isLoading = login.isPending || register.isPending || registerWithInvitation.isPending;

  function resetForm() {
    setEmail('');
    setPassword('');
    setPasswordConfirm('');
    setName('');
    setFamilyName('');
    setInvitationCode('');
    setError('');
  }

  function switchTab(t: Tab) {
    resetForm();
    setTab(t);
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await login.mutateAsync({ email, password });
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Anmeldung fehlgeschlagen';
      setError(msg);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen lang sein');
      return;
    }

    if (password !== passwordConfirm) {
      setError('Passwörter stimmen nicht überein');
      return;
    }

    try {
      if (invitationCode.trim()) {
        await registerWithInvitation.mutateAsync({
          email,
          password,
          password_confirm: passwordConfirm,
          name,
          invitation_code: invitationCode.trim(),
        });
      } else {
        await register.mutateAsync({
          email,
          password,
          name,
          family_name: familyName,
        });
      }
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Registrierung fehlgeschlagen';
      setError(msg);
    }
  }

  const strength = getPasswordStrength(password);
  const strengthCfg = STRENGTH_CONFIG[strength];

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-600 via-indigo-700 to-[#1E1B4B] px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm">
            <Shield className="h-9 w-9 text-white" />
          </div>
          <h1 className="mt-4 text-3xl font-bold text-white">Heimdall</h1>
          <p className="mt-1 text-sm text-indigo-200">
            Digitaler Kinderschutz für die ganze Familie
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          {/* Tabs */}
          <div className="mb-6 flex rounded-lg bg-slate-100 p-1">
            <button
              onClick={() => switchTab('login')}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                tab === 'login'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Anmelden
            </button>
            <button
              onClick={() => switchTab('register')}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                tab === 'register'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Registrieren
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Login Form */}
          {tab === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  E-Mail
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="eltern@beispiel.de"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Passwort
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Mindestens 8 Zeichen"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 pr-10 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                Anmelden
              </button>
            </form>
          )}

          {/* Register Form */}
          {tab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4">
              {/* Invitation Code (optional) */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Einladungscode <span className="text-slate-400">(optional)</span>
                </label>
                <input
                  type="text"
                  value={invitationCode}
                  onChange={(e) => setInvitationCode(e.target.value.toUpperCase())}
                  placeholder="z.B. ODIN-3382"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-mono text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
                {invitationCode.trim() && (
                  <p className="mt-1 text-xs text-indigo-600">
                    Sie treten einer bestehenden Familie bei.
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Vorname
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Max"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Family name — only shown when no invitation code */}
              {!invitationCode.trim() && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Familienname
                  </label>
                  <input
                    type="text"
                    required
                    value={familyName}
                    onChange={(e) => setFamilyName(e.target.value)}
                    placeholder="Mustermann"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              )}

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  E-Mail
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="eltern@beispiel.de"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Passwort
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Mindestens 8 Zeichen"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 pr-10 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {/* Password strength indicator */}
                {password && (
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
                  Passwort wiederholen
                </label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  placeholder="Passwort bestätigen"
                  className={`w-full rounded-lg border px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 ${
                    passwordConfirm && password !== passwordConfirm
                      ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
                      : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500/20'
                  }`}
                />
                {passwordConfirm && password !== passwordConfirm && (
                  <p className="mt-1 text-xs text-red-600">Passwörter stimmen nicht überein</p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                Registrieren
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-indigo-300">
          Heimdall Kinderschutz &mdash; Sicherheit für die digitale Welt
        </p>
      </div>
    </div>
  );
}
