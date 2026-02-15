import { useNavigate } from 'react-router-dom';
import {
  Users,
  Shield,
  Ticket,
  Clock,
  Plus,
  ArrowRight,
  Loader2,
  AlertCircle,
  Trophy,
  Flame,
  Monitor,
  BarChart3,
} from 'lucide-react';
import { useChildren } from '../hooks/useChildren';
import { useFamilyDashboard, useChildDashboard } from '../hooks/useAnalytics';
import type { User } from '../types';

const FAMILY_ID = 'demo';

function ChildCard({ child }: { child: User }) {
  const navigate = useNavigate();
  const { data: stats } = useChildDashboard(child.id);

  const usageMinutes = stats?.usage_today_minutes ?? 0;
  const limitMinutes = stats?.daily_limit_minutes;
  const usagePercent = limitMinutes ? Math.min(100, Math.round((usageMinutes / limitMinutes) * 100)) : null;
  const usageColor = usagePercent !== null
    ? usagePercent >= 90 ? 'text-red-600' : usagePercent >= 70 ? 'text-amber-600' : 'text-emerald-600'
    : 'text-slate-700';

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 text-lg font-bold text-indigo-600">
          {child.name.charAt(0).toUpperCase()}
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-900">{child.name}</h3>
          {child.age != null && (
            <p className="text-sm text-slate-500">{child.age} Jahre</p>
          )}
        </div>
        {stats && stats.devices_online > 0 && (
          <div className="flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">
            <Monitor className="h-3 w-3" />
            Online
          </div>
        )}
      </div>

      {/* Stats grid */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            Nutzung heute
          </div>
          <p className={`mt-1 text-sm font-semibold ${usageColor}`}>
            {stats ? (
              limitMinutes
                ? `${usageMinutes} / ${limitMinutes} Min`
                : `${usageMinutes} Min`
            ) : (
              'Keine Daten'
            )}
          </p>
          {usagePercent !== null && (
            <div className="mt-1.5 h-1.5 w-full rounded-full bg-slate-200">
              <div
                className={`h-full rounded-full ${usagePercent >= 90 ? 'bg-red-500' : usagePercent >= 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${usagePercent}%` }}
              />
            </div>
          )}
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Ticket className="h-3.5 w-3.5" />
            Aktive TANs
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-700">
            {stats?.active_tans ?? 0}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Trophy className="h-3.5 w-3.5" />
            Quests heute
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-700">
            {stats?.quests_completed_today ?? 0}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Flame className="h-3.5 w-3.5" />
            Streak
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-700">
            {stats?.current_streak ?? 0} {(stats?.current_streak ?? 0) === 1 ? 'Tag' : 'Tage'}
          </p>
        </div>
      </div>

      {stats?.top_group && (
        <p className="mb-3 text-xs text-slate-400">
          Meistgenutzt: <span className="font-medium text-slate-600">{stats.top_group}</span>
        </p>
      )}

      {/* Quick actions */}
      <div className="flex gap-2">
        <button
          onClick={() => navigate(`/tans/${child.id}`)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-600 transition-colors hover:bg-indigo-100"
        >
          <Plus className="h-3.5 w-3.5" />
          TAN
        </button>
        <button
          onClick={() => navigate(`/rules/${child.id}`)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
        >
          <Shield className="h-3.5 w-3.5" />
          Regeln
        </button>
        <button
          onClick={() => navigate(`/devices/${child.id}`)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
        >
          <Monitor className="h-3.5 w-3.5" />
          Gerate
        </button>
      </div>

      {/* Detail link */}
      <button
        onClick={() => navigate(`/analytics/${child.id}`)}
        className="mt-3 flex w-full items-center justify-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
      >
        <BarChart3 className="h-3 w-3" />
        Analytik anzeigen
        <ArrowRight className="h-3 w-3" />
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: children, isLoading, isError, error } = useChildren(FAMILY_ID);
  const { data: familyStats } = useFamilyDashboard(FAMILY_ID);

  return (
    <div className="mx-auto max-w-6xl">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Übersicht über alle Kinder und deren Aktivitäten
        </p>
      </div>

      {/* Summary cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
              <Users className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">
                {familyStats?.total_children ?? children?.length ?? 0}
              </p>
              <p className="text-xs text-slate-500">Kinder</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
              <Shield className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">
                {familyStats?.total_active_rules ?? 0}
              </p>
              <p className="text-xs text-slate-500">Aktive Regeln</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100">
              <Ticket className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">
                {familyStats?.tans_today ?? 0}
              </p>
              <p className="text-xs text-slate-500">TANs heute</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100">
              <Clock className="h-5 w-5 text-violet-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">
                {familyStats?.total_usage_today_minutes ?? 0}
              </p>
              <p className="text-xs text-slate-500">Minuten heute</p>
            </div>
          </div>
        </div>
      </div>

      {/* Children grid */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
          <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
          <p className="text-sm font-medium text-red-700">
            Fehler beim Laden: {(error as Error)?.message ?? 'Unbekannter Fehler'}
          </p>
        </div>
      )}

      {!isLoading && !isError && children && children.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <Users className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Noch keine Kinder angelegt
          </h3>
          <p className="mt-1 mb-6 text-sm text-slate-500">
            Legen Sie Ihr erstes Kind an, um Regeln und TANs zu verwalten.
          </p>
          <button
            onClick={() => navigate('/children')}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Kind hinzufügen
          </button>
        </div>
      )}

      {!isLoading && !isError && children && children.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">
              Kinder
            </h2>
            <button
              onClick={() => navigate('/children')}
              className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              Alle verwalten
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {children.map((child) => (
              <ChildCard key={child.id} child={child} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
