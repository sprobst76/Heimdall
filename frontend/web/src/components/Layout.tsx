import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Shield,
  Ticket,
  Grid3x3,
  Trophy,
  Gift,
  ClipboardCheck,
  Brain,
  CalendarDays,
  BarChart3,
  Monitor,
  LogOut,
  Menu,
  X,
  ChevronDown,
  ChevronRight,
  UserCog,
  CalendarClock,
  ShieldCheck,
} from 'lucide-react';
import { useLogout, useFamilyId } from '../hooks/useAuth';
import { useChildren } from '../hooks/useChildren';
import { useDashboardWebSocket } from '../hooks/useWebSocket';
import { NotificationContext, useNotificationState } from '../hooks/useNotifications';
import NotificationToast from './NotificationToast';

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [childrenExpanded, setChildrenExpanded] = useState(true);
  const logout = useLogout();
  const navigate = useNavigate();
  const familyId = useFamilyId();
  const { data: children } = useChildren(familyId);
  const notificationState = useNotificationState();
  const { isConnected } = useDashboardWebSocket({
    onNotification: (data) => {
      notificationState.addNotification({
        title: data.title,
        message: data.message,
        category: data.category as 'info' | 'quest' | 'tan' | 'device',
      });
    },
  });

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-600 text-white'
        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
    }`;

  const childNavClasses = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${
      isActive
        ? 'bg-slate-700 text-indigo-400'
        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
    }`;

  return (
    <NotificationContext.Provider value={notificationState}>
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <NotificationToast />
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-900 transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-5">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2"
          >
            <Shield className="h-7 w-7 text-indigo-400" />
            <span className="text-lg font-bold tracking-wide text-white">
              HEIMDALL
            </span>
          </button>
          <button
            className="text-slate-400 hover:text-white lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <NavLink to="/" end className={navLinkClasses} onClick={() => setSidebarOpen(false)}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>

          <NavLink to="/children" className={navLinkClasses} onClick={() => setSidebarOpen(false)}>
            <Users className="h-4 w-4" />
            Kinder
          </NavLink>

          <NavLink to="/quest-reviews" className={navLinkClasses} onClick={() => setSidebarOpen(false)}>
            <ClipboardCheck className="h-4 w-4" />
            Quest-Prüfung
          </NavLink>

          <NavLink to="/ai-assistant" className={navLinkClasses} onClick={() => setSidebarOpen(false)}>
            <Brain className="h-4 w-4" />
            KI-Assistent
          </NavLink>

          <NavLink to="/holidays" className={navLinkClasses} onClick={() => setSidebarOpen(false)}>
            <CalendarDays className="h-4 w-4" />
            Kalender
          </NavLink>

          <NavLink to="/family" className={navLinkClasses} onClick={() => setSidebarOpen(false)}>
            <Users className="h-4 w-4" />
            Familie
          </NavLink>

          {/* Children section */}
          {children && children.length > 0 && (
            <div className="mt-6">
              <button
                onClick={() => setChildrenExpanded(!childrenExpanded)}
                className="flex w-full items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-300"
              >
                {childrenExpanded ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
                Kinder verwalten
              </button>

              {childrenExpanded &&
                children.map((child) => (
                  <div key={child.id} className="mb-3">
                    <div className="px-4 py-1.5 text-sm font-semibold text-slate-200">
                      {child.name}
                      {child.age != null && (
                        <span className="ml-1 text-xs font-normal text-slate-500">
                          ({child.age} J.)
                        </span>
                      )}
                    </div>
                    <div className="ml-2 space-y-0.5">
                      <NavLink
                        to={`/rules/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <Shield className="h-3.5 w-3.5" />
                        Zeitregeln
                      </NavLink>
                      <NavLink
                        to={`/tans/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <Ticket className="h-3.5 w-3.5" />
                        TANs
                      </NavLink>
                      <NavLink
                        to={`/tan-schedules/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <CalendarClock className="h-3.5 w-3.5" />
                        TAN-Regeln
                      </NavLink>
                      <NavLink
                        to={`/totp/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <ShieldCheck className="h-3.5 w-3.5" />
                        TOTP
                      </NavLink>
                      <NavLink
                        to={`/app-groups/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <Grid3x3 className="h-3.5 w-3.5" />
                        App-Gruppen
                      </NavLink>
                      <NavLink
                        to={`/quests/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <Trophy className="h-3.5 w-3.5" />
                        Quests
                      </NavLink>
                      <NavLink
                        to={`/usage-rewards/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <Gift className="h-3.5 w-3.5" />
                        Belohnungen
                      </NavLink>
                      <NavLink
                        to={`/devices/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <Monitor className="h-3.5 w-3.5" />
                        Geräte
                      </NavLink>
                      <NavLink
                        to={`/analytics/${child.id}`}
                        className={childNavClasses}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <BarChart3 className="h-3.5 w-3.5" />
                        Analytik
                      </NavLink>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </nav>

        {/* Profile + Logout */}
        <div className="border-t border-slate-800 p-3 space-y-1">
          <NavLink
            to="/profile"
            className={navLinkClasses}
            onClick={() => setSidebarOpen(false)}
          >
            <UserCog className="h-4 w-4" />
            Profil
          </NavLink>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Abmelden
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-8">
          <button
            className="text-slate-600 hover:text-slate-900 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <h1 className="text-lg font-semibold text-slate-800 lg:text-xl">
            Eltern-Portal
          </h1>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 text-sm text-slate-500 sm:flex">
              <span
                className={`inline-block h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-slate-300'}`}
                title={isConnected ? 'Live-Verbindung aktiv' : 'Keine Live-Verbindung'}
              />
              Heimdall Kinderschutz
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
    </NotificationContext.Provider>
  );
}
