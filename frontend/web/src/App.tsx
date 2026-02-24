import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';        // eager — always needed
import DashboardPage from './pages/DashboardPage'; // eager — first page after login

// Lazy-loaded routes — downloaded on first navigation to that page
const ChildrenPage       = lazy(() => import('./pages/ChildrenPage'));
const RulesPage          = lazy(() => import('./pages/RulesPage'));
const TansPage           = lazy(() => import('./pages/TansPage'));
const AppGroupsPage      = lazy(() => import('./pages/AppGroupsPage'));
const QuestsPage         = lazy(() => import('./pages/QuestsPage'));
const QuestReviewPage    = lazy(() => import('./pages/QuestReviewPage'));
const AIAssistantPage    = lazy(() => import('./pages/AIAssistantPage'));
const AnalyticsPage      = lazy(() => import('./pages/AnalyticsPage'));
const DevicesPage        = lazy(() => import('./pages/DevicesPage'));
const UsageRewardsPage   = lazy(() => import('./pages/UsageRewardsPage'));
const TanSchedulesPage   = lazy(() => import('./pages/TanSchedulesPage'));
const TotpPage           = lazy(() => import('./pages/TotpPage'));
const HolidaysPage       = lazy(() => import('./pages/HolidaysPage'));
const FamilySettingsPage = lazy(() => import('./pages/FamilySettingsPage'));
const ProfilePage        = lazy(() => import('./pages/ProfilePage'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<DashboardPage />} />
              <Route path="children" element={<ChildrenPage />} />
              <Route path="rules/:childId" element={<RulesPage />} />
              <Route path="tans/:childId" element={<TansPage />} />
              <Route path="app-groups/:childId" element={<AppGroupsPage />} />
              <Route path="quests/:childId" element={<QuestsPage />} />
              <Route path="quest-reviews" element={<QuestReviewPage />} />
              <Route path="ai-assistant" element={<AIAssistantPage />} />
              <Route path="devices/:childId" element={<DevicesPage />} />
              <Route path="usage-rewards/:childId" element={<UsageRewardsPage />} />
              <Route path="tan-schedules/:childId" element={<TanSchedulesPage />} />
              <Route path="totp/:childId" element={<TotpPage />} />
              <Route path="holidays" element={<HolidaysPage />} />
              <Route path="family" element={<FamilySettingsPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="analytics/:childId" element={<AnalyticsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
