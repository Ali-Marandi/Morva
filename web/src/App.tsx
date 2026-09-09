import React, { ReactNode } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Auth from "./pages/Auth";
import Employees from "./pages/Employees";
import Payroll from "./pages/Payroll";
import Approvals from "./pages/Approvals";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import SelfService from "./pages/SelfService";
import Objections from "./pages/Objections";
import NotFound from "./pages/NotFound";
import { authService } from "./services";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 1000 * 60 * 5, gcTime: 1000 * 60 * 10, retry: 1, refetchOnWindowFocus: false },
    mutations: { retry: 1 },
  },
});

interface ProtectedRouteProps { children: ReactNode; }

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  if (!authService.isAuthenticated()) return <Navigate to="/auth" replace />;
  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router basename="/Morva">
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/employees" element={<Employees />} />
            <Route path="/self-service" element={<SelfService />} />
            <Route path="/objections" element={<Objections />} />
            <Route path="/payroll" element={<Payroll />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
