import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import RulesPage from './pages/RulesPage';
import TansPage from './pages/TansPage';
import AppGroupsPage from './pages/AppGroupsPage';
import ChildrenPage from './pages/ChildrenPage';
import QuestsPage from './pages/QuestsPage';
import QuestReviewPage from './pages/QuestReviewPage';
import AIAssistantPage from './pages/AIAssistantPage';
import AnalyticsPage from './pages/AnalyticsPage';
import DevicesPage from './pages/DevicesPage';
import UsageRewardsPage from './pages/UsageRewardsPage';

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
            <Route path="analytics/:childId" element={<AnalyticsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
