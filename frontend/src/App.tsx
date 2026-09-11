import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import AdminDashboard from './pages/AdminDashboard';
import AdminClients from './pages/AdminClients';
import AdminClientDetails from './pages/AdminClientDetails';
import AdminUsage from './pages/AdminUsage';
import ClientData from './pages/ClientData';
import ClientAnalytics from './pages/ClientAnalytics';
import ClientAIInsights from './pages/ClientAIInsights';
import ClientReports from './pages/ClientReports';
import ClientProfile from './pages/ClientProfile';

// Helper to check if a JWT token exists, is well-formed, and is not expired
function isTokenValid(token: string | null): boolean {
  if (!token || token.trim() === '' || token === 'undefined' || token === 'null') {
    return false;
  }
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return false;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    if (payload.exp && Date.now() >= payload.exp * 1000) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

// Auth Guard for Public Pages (Login / Signup):
// If user is already authenticated, redirect to their role dashboard
const PublicAuthRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  if (isTokenValid(token) && role && role !== 'undefined' && role !== 'null') {
    return role === 'ADMIN'
      ? <Navigate to="/admin/dashboard" replace />
      : <Navigate to="/client/dashboard" replace />;
  }

  return <>{children}</>;
};

// Auth Guard: Verifies login token and validates role-based permissions
const AuthenticatedRoute = ({ allowedRoles }: { allowedRoles: string[] }) => {
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  if (!isTokenValid(token) || !role || role === 'undefined' || role === 'null') {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('userName');
    return <Navigate to="/login?expired=1" replace />;
  }

  if (!allowedRoles.includes(role)) {
    // Redirect unauthorized user to their own proper portal dashboard
    return role === 'ADMIN' 
      ? <Navigate to="/admin/dashboard" replace /> 
      : <Navigate to="/client/dashboard" replace />;
  }

  return <Outlet />;
};

// Portal Layout structure containing sidebar, header, and page content outlets
const PortalLayout = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0f19]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

// Helper redirect for /dashboard route
const DashboardRedirect = () => {
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  if (!isTokenValid(token) || !role || role === 'undefined' || role === 'null') {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('userName');
    return <Navigate to="/login" replace />;
  }

  return role === 'ADMIN'
    ? <Navigate to="/admin/dashboard" replace />
    : <Navigate to="/client/dashboard" replace />;
};

// Main routing configuration
export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public SaaS Landing Page */}
        <Route path="/" element={<LandingPage />} />

        {/* Public authentication pages */}
        <Route
          path="/login"
          element={
            <PublicAuthRoute>
              <Login />
            </PublicAuthRoute>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicAuthRoute>
              <SignUp />
            </PublicAuthRoute>
          }
        />

        {/* Generic /dashboard redirect */}
        <Route path="/dashboard" element={<DashboardRedirect />} />

        {/* Admin protected console endpoints */}
        <Route element={<AuthenticatedRoute allowedRoles={['ADMIN']} />}>
          <Route element={<PortalLayout />}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/clients" element={<AdminClients />} />
            <Route path="/admin/clients/:id" element={<AdminClientDetails />} />
            <Route path="/admin/analytics" element={<AdminUsage />} />
          </Route>
        </Route>

        {/* Client protected portals and visualization hubs */}
        <Route element={<AuthenticatedRoute allowedRoles={['CLIENT']} />}>
          <Route element={<PortalLayout />}>
            <Route path="/client/dashboard" element={<ClientAnalytics />} />
            <Route path="/client/data" element={<ClientData />} />
            <Route path="/client/analytics" element={<ClientAnalytics />} />
            <Route path="/client/insights" element={<ClientAIInsights />} />
            <Route path="/client/reports" element={<ClientReports />} />
            <Route path="/client/profile" element={<ClientProfile />} />
          </Route>
        </Route>

        {/* Fallbacks to Landing Page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
