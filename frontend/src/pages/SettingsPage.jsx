import React from "react";
import { useAuth } from "../services/AuthContext.jsx";

export default function SettingsPage() {
  const { user } = useAuth();
  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-xl font-semibold text-ink-900 mb-1">Settings</h1>
      <p className="text-sm text-ink-500 mb-4">Account and application configuration.</p>
      <div className="card p-4 space-y-2 text-sm">
        <div><span className="text-ink-500">Username:</span> {user?.username}</div>
        <div><span className="text-ink-500">Role:</span> {user?.role}</div>
        <div><span className="text-ink-500">Email:</span> {user?.email || "—"}</div>
      </div>
      <div className="card p-4 mt-4 text-sm text-ink-600">
        Source reliability weights, confidence thresholds, and the project target CRS are
        configured server-side (see backend <code>settings.GEOHARMONIZE</code>) and via the
        Attribute Mapping admin screen — not editable here in the MVP.
      </div>
    </div>
  );
}
