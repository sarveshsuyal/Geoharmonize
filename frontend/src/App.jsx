import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./layouts/AppLayout.jsx";
import { useAuth } from "./services/AuthContext.jsx";

import LoginPage from "./pages/LoginPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import DatasetsPage from "./pages/DatasetsPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import MapPage from "./pages/MapPage.jsx";
import HarmonizationPage from "./pages/HarmonizationPage.jsx";
import ConflictsPage from "./pages/ConflictsPage.jsx";
import ReviewQueuePage from "./pages/ReviewQueuePage.jsx";
import ChangeDetectionPage from "./pages/ChangeDetectionPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-ink-500 text-sm">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/harmonization" element={<HarmonizationPage />} />
        <Route path="/conflicts" element={<ConflictsPage />} />
        <Route path="/review" element={<ReviewQueuePage />} />
        <Route path="/change-detection" element={<ChangeDetectionPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
