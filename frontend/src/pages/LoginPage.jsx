import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../services/AuthContext.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-ink-900 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="text-2xl font-semibold text-white">GeoHarmonize</div>
          <div className="text-xs text-ink-200 mt-1">
            Department of Land Resources · Ministry of Rural Development
          </div>
        </div>
        <form onSubmit={handleSubmit} className="card bg-white p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-ink-600 mb-1">Username</label>
            <input
              className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-ink-600 mb-1">Password</label>
            <input
              type="password"
              className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <div className="text-sm text-status-low">{error}</div>}
          <button type="submit" disabled={busy} className="btn-primary w-full justify-center">
            {busy ? "Signing in..." : "Sign in"}
          </button>
          <div className="text-center text-xs text-ink-500 pt-2 border-t border-ink-100">
            Default credentials: <span className="font-semibold text-ink-700">sarvesh</span> / <span className="font-semibold text-ink-700">sarvesh@suyal</span>
          </div>
        </form>
      </div>
    </div>
  );
}
