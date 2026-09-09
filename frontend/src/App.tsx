import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import AdminClients from './pages/AdminClients';
import AdminClientDetails from './pages/AdminClientDetails';
import AdminUsage from './pages/AdminUsage';
import ClientData from './pages/ClientData';
import ClientAnalytics from './pages/ClientAnalytics';
import ClientAIInsights from './pages/ClientAIInsights';
import ClientReports from './pages/ClientReports';
import ClientProfile from './pages/ClientProfile';

// Auth Guard: Verifies login token and validates role-based permissions
const AuthenticatedRoute = ({ allowedRoles }: { allowedRoles: string[] }) => {
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  if (!token || !role) {
    return <Navigate to="/login" replace />;
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

// Main routing configuration
export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public login page */}
        <Route path="/login" element={<Login />} />

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

        {/* Fallbacks */}
        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<RootRedirect />} />
      </Routes>
    </Router>
  );
}

const RootRedirect = () => {
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  if (!token || !role) {
    return <Navigate to="/login" replace />;
  }

  return role === 'ADMIN' 
    ? <Navigate to="/admin/dashboard" replace /> 
    : <Navigate to="/client/dashboard" replace />;
};
