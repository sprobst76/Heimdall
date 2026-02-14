import { useParams, Link } from 'react-router-dom';
import {
  Monitor,
  Smartphone,
  Shield,
  ShieldOff,
  ShieldAlert,
  Loader2,
  AlertCircle,
  ChevronLeft,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useChildren } from '../hooks/useChildren';
import {
  useChildDevices,
  useBlockAllDevices,
  useBlockDevice,
  useUnblockDevice,
} from '../hooks/useDevices';
import type { Device } from '../types';

const FAMILY_ID = 'demo';

function deviceIcon(type: string) {
  switch (type) {
    case 'android':
    case 'ios':
      return <Smartphone className="h-5 w-5" />;
    default:
      return <Monitor className="h-5 w-5" />;
  }
}

function statusBadge(status: string): { label: string; color: string; icon: React.ReactNode } {
  switch (status) {
    case 'active':
      return {
        label: 'Aktiv',
        color: 'bg-emerald-100 text-emerald-700',
        icon: <Wifi className="h-3 w-3" />,
      };
    case 'blocked':
      return {
        label: 'Gesperrt',
        color: 'bg-red-100 text-red-700',
        icon: <ShieldAlert className="h-3 w-3" />,
      };
    default:
      return {
        label: status,
        color: 'bg-slate-100 text-slate-600',
        icon: <WifiOff className="h-3 w-3" />,
      };
  }
}

function DeviceCard({
  device,
  childId,
}: {
  device: Device;
  childId: string;
}) {
  const blockDevice = useBlockDevice(childId);
  const unblockDevice = useUnblockDevice(childId);
  const badge = statusBadge(device.status);
  const isBlocked = device.status === 'blocked';
  const isPending = blockDevice.isPending || unblockDevice.isPending;

  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
          {deviceIcon(device.type)}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-900">
              {device.name}
            </h3>
            <span
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${badge.color}`}
            >
              {badge.icon}
              {badge.label}
            </span>
          </div>
          <div className="mt-1 flex gap-3 text-xs text-slate-400">
            <span className="capitalize">{device.type}</span>
            {device.last_seen && (
              <span>
                Zuletzt:{' '}
                {new Date(device.last_seen).toLocaleString('de-DE', {
                  dateStyle: 'short',
                  timeStyle: 'short',
                })}
              </span>
            )}
          </div>
        </div>
      </div>

      <button
        onClick={() =>
          isBlocked
            ? unblockDevice.mutate(device.id)
            : blockDevice.mutate(device.id)
        }
        disabled={isPending}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors disabled:opacity-50 ${
          isBlocked
            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            : 'bg-red-50 text-red-700 hover:bg-red-100'
        }`}
      >
        {isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : isBlocked ? (
          <ShieldOff className="h-3.5 w-3.5" />
        ) : (
          <Shield className="h-3.5 w-3.5" />
        )}
        {isBlocked ? 'Entsperren' : 'Sperren'}
      </button>
    </div>
  );
}

export default function DevicesPage() {
  const { childId } = useParams<{ childId: string }>();
  const { data: children } = useChildren(FAMILY_ID);
  const child = children?.find((c) => c.id === childId);

  const {
    data: devices,
    isLoading,
    isError,
    error,
  } = useChildDevices(childId ?? '');

  const blockAll = useBlockAllDevices(childId ?? '');

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
          <h1 className="text-2xl font-bold text-slate-900">
            Gerate{child ? ` - ${child.name}` : ''}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Gerate verwalten, sperren und entsperren
          </p>
        </div>
        <button
          onClick={() => blockAll.mutate()}
          disabled={blockAll.isPending || !devices?.length}
          className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-50"
        >
          {blockAll.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ShieldAlert className="h-4 w-4" />
          )}
          Alle sperren
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
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
      {!isLoading && !isError && devices && devices.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
          <Monitor className="mb-4 h-12 w-12 text-slate-300" />
          <h3 className="text-lg font-semibold text-slate-700">
            Keine Gerate registriert
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Gerate werden automatisch beim ersten Verbinden registriert.
          </p>
        </div>
      )}

      {/* Device list */}
      <div className="space-y-3">
        {devices?.map((device) => (
          <DeviceCard key={device.id} device={device} childId={childId} />
        ))}
      </div>
    </div>
  );
}
