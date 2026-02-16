import { Trophy, Ticket, Monitor, Bell, X } from 'lucide-react';
import { useNotifications, type Notification } from '../hooks/useNotifications';

const CATEGORY_CONFIG: Record<
  Notification['category'],
  { icon: typeof Bell; bg: string; border: string; text: string; iconColor: string }
> = {
  quest: {
    icon: Trophy,
    bg: 'bg-violet-50',
    border: 'border-violet-200',
    text: 'text-violet-800',
    iconColor: 'text-violet-500',
  },
  tan: {
    icon: Ticket,
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
    iconColor: 'text-amber-500',
  },
  device: {
    icon: Monitor,
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-800',
    iconColor: 'text-emerald-500',
  },
  info: {
    icon: Bell,
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    text: 'text-indigo-800',
    iconColor: 'text-indigo-500',
  },
};

export default function NotificationToast() {
  const { notifications, dismissNotification } = useNotifications();

  if (notifications.length === 0) return null;

  return (
    <div className="fixed right-4 top-4 z-50 flex flex-col gap-2">
      {notifications.map((n) => {
        const cfg = CATEGORY_CONFIG[n.category] ?? CATEGORY_CONFIG.info;
        const Icon = cfg.icon;

        return (
          <div
            key={n.id}
            className={`flex w-80 items-start gap-3 rounded-xl border ${cfg.border} ${cfg.bg} p-4 shadow-lg animate-in slide-in-from-right`}
          >
            <Icon className={`mt-0.5 h-5 w-5 flex-shrink-0 ${cfg.iconColor}`} />
            <div className="min-w-0 flex-1">
              <p className={`text-sm font-semibold ${cfg.text}`}>{n.title}</p>
              <p className={`mt-0.5 text-xs ${cfg.text} opacity-80`}>{n.message}</p>
            </div>
            <button
              onClick={() => dismissNotification(n.id)}
              className={`flex-shrink-0 rounded p-0.5 ${cfg.text} opacity-60 hover:opacity-100`}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
