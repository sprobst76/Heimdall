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
} from 'lucide-react';
import { useChildren } from '../hooks/useChildren';
import type { User } from '../types';

const FAMILY_ID = 'demo';

function ChildCard({ child }: { child: User }) {
  const navigate = useNavigate();

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 text-lg font-bold text-indigo-600">
          {child.name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{child.name}</h3>
          {child.age != null && (
            <p className="text-sm text-slate-500">{child.age} Jahre</p>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            Nutzung heute
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-700">
            Noch keine Daten
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Ticket className="h-3.5 w-3.5" />
            Aktive TANs
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-700">&mdash;</p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex gap-2">
        <button
          onClick={() => navigate(`/tans/${child.id}`)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-600 transition-colors hover:bg-indigo-100"
        >
          <Plus className="h-3.5 w-3.5" />
          TAN erstellen
        </button>
        <button
          onClick={() => navigate(`/rules/${child.id}`)}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200"
        >
          <Shield className="h-3.5 w-3.5" />
          Regeln
        </button>
      </div>

      {/* Detail link */}
      <button
        onClick={() => navigate(`/rules/${child.id}`)}
        className="mt-3 flex w-full items-center justify-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
      >
        Alle Details anzeigen
        <ArrowRight className="h-3 w-3" />
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: children, isLoading, isError, error } = useChildren(FAMILY_ID);

  return (
    <div className="mx-auto max-w-6xl">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Ubersicht uber alle Kinder und deren Aktivitaten
        </p>
      </div>

      {/* Summary cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
              <Users className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">
                {children?.length ?? 0}
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
              <p className="text-2xl font-bold text-slate-900">&mdash;</p>
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
              <p className="text-2xl font-bold text-slate-900">&mdash;</p>
              <p className="text-xs text-slate-500">TANs heute</p>
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
            Kind hinzufugen
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
