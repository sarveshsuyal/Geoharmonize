import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../services/AuthContext.jsx";
import { getApiBaseUrl, setApiBaseUrl, checkBackendHealth } from "../services/api.js";
import {
  Map as MapIcon,
  ShieldCheck,
  Server,
  Activity,
  ArrowRight,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
  Sliders,
  Sparkles,
} from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("sarvesh");
  const [password, setPassword] = useState("sarvesh@suyal");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [coldStartActive, setColdStartActive] = useState(false);

  // Backend connection status
  const [currentApiUrl, setCurrentApiUrl] = useState(getApiBaseUrl());
  const [showConfig, setShowConfig] = useState(false);
  const [customUrlInput, setCustomUrlInput] = useState(getApiBaseUrl());
  const [healthStatus, setHealthStatus] = useState({ checking: true, ok: false, latency: null });

  async function testBackend() {
    setHealthStatus({ checking: true, ok: false, latency: null });
    const result = await checkBackendHealth();
    setHealthStatus({
      checking: false,
      ok: result.ok,
      latency: result.latency,
      data: result.data,
      error: result.error,
    });
  }

  useEffect(() => {
    testBackend();
  }, [currentApiUrl]);

  function handleSaveApiUrl(e) {
    e.preventDefault();
    setApiBaseUrl(customUrlInput);
    setCurrentApiUrl(getApiBaseUrl());
    testBackend();
    setShowConfig(false);
  }

  function handleQuickFill() {
    setUsername("sarvesh");
    setPassword("sarvesh@suyal");
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setColdStartActive(false);

    // If backend is on Render free tier, cold starts take ~30-45s
    const isRender = currentApiUrl.includes("onrender.com");
    let timer = null;
    if (isRender) {
      timer = setTimeout(() => {
        setColdStartActive(true);
      }, 5000);
    }

    try {
      await login(username, password);
      if (timer) clearTimeout(timer);
      navigate("/dashboard");
    } catch (err) {
      if (timer) clearTimeout(timer);
      setColdStartActive(false);

      if (!err.response) {
        if (isRender) {
          setError(
            "Could not reach the Render backend. If the service is waking up from free-tier sleep, please wait 30 seconds and try again."
          );
        } else {
          setError(
            `Could not reach API at ${currentApiUrl}. Ensure your backend server is running.`
          );
        }
      } else if (err.response?.data?.non_field_errors) {
        setError(err.response.data.non_field_errors.join(" "));
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Invalid username or password. Please verify credentials.");
      }
    } finally {
      setBusy(false);
    }
  }

  const isRenderCloud = currentApiUrl.includes("onrender.com");

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between text-slate-100 relative overflow-hidden">
      {/* Background Subtle Gradient Blobs */}
      <div className="absolute top-0 -left-40 w-96 h-96 bg-sky-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 -right-40 w-96 h-96 bg-teal-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Ministry Banner */}
      <header className="px-6 py-4 border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-600 to-teal-400 flex items-center justify-center shadow">
            <MapIcon className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              GeoHarmonize
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-300 border border-sky-400/30">
                SIH26013
              </span>
            </div>
            <div className="text-[11px] text-slate-400">
              Department of Land Resources · Ministry of Rural Development
            </div>
          </div>
        </div>

        {/* Backend Live Indicator */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700 hover:border-slate-600 transition-colors"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                healthStatus.checking
                  ? "bg-amber-400 animate-pulse"
                  : healthStatus.ok
                  ? "bg-emerald-400 animate-pulse"
                  : "bg-rose-400"
              }`}
            />
            <span className="text-slate-300">
              {healthStatus.checking
                ? "Pinging Backend..."
                : healthStatus.ok
                ? `${isRenderCloud ? "Render Cloud" : "Local API"} (${healthStatus.latency}ms)`
                : "Backend Offline"}
            </span>
            <Sliders className="w-3 h-3 text-slate-400 ml-1" />
          </button>
        </div>
      </header>

      {/* Main Center Card */}
      <main className="flex-1 flex items-center justify-center px-4 py-8 relative z-10">
        <div className="w-full max-w-md">
          {/* Custom Backend URL Configuration Panel (Dropdown/Collapsible) */}
          {showConfig && (
            <div className="mb-4 bg-slate-900 border border-slate-700/80 rounded-xl p-4 shadow-xl text-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <Server className="w-3.5 h-3.5 text-sky-400" />
                  Backend API Endpoint Configuration
                </span>
                <button
                  type="button"
                  onClick={testBackend}
                  className="text-sky-400 hover:text-sky-300 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  Re-test
                </button>
              </div>
              <p className="text-slate-400 leading-relaxed">
                Connect this UI to your deployed Render service (e.g.{" "}
                <code className="text-sky-300">https://geoharmonize-backend.onrender.com/api</code>) or local
                Docker backend.
              </p>
              <form onSubmit={handleSaveApiUrl} className="space-y-2">
                <input
                  type="url"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  value={customUrlInput}
                  onChange={(e) => setCustomUrlInput(e.target.value)}
                  placeholder="https://your-service.onrender.com/api"
                  required
                />
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setCustomUrlInput("http://localhost:8000/api");
                      setApiBaseUrl("http://localhost:8000/api");
                      setCurrentApiUrl("http://localhost:8000/api");
                      testBackend();
                    }}
                    className="px-2.5 py-1 text-slate-400 hover:text-slate-200"
                  >
                    Reset to Local
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded-md font-medium"
                  >
                    Save & Test
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Login Card */}
          <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl">
            <div className="text-center mb-6">
              <div className="w-12 h-12 mx-auto rounded-xl bg-gradient-to-tr from-sky-500 to-teal-400 flex items-center justify-center shadow-lg shadow-sky-600/20 mb-3">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-xl font-bold text-white tracking-tight">GIS Officer Portal</h1>
              <p className="text-xs text-slate-400 mt-1">
                Enter your credentials to access the harmonization console
              </p>
            </div>

            {/* Render Cold-Start Alert */}
            {coldStartActive && (
              <div className="mb-4 p-3 rounded-lg bg-sky-950/60 border border-sky-800/80 text-xs text-sky-200 flex items-start gap-2.5">
                <RefreshCw className="w-4 h-4 text-sky-400 animate-spin shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-sky-100">Waking up Render backend...</div>
                  <div className="text-[11px] text-sky-300/80 mt-0.5">
                    Render free-tier instances sleep when inactive. Waking up takes ~30–45 seconds on first request.
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-rose-950/50 border border-rose-800/70 text-xs text-rose-200 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="leading-snug">{error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Username or Email
                </label>
                <input
                  type="text"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-sky-500 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 transition-colors"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="sarvesh or sarvesh112k@gmail.com"
                  required
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="block text-xs font-medium text-slate-300">Password</label>
                </div>
                <input
                  type="password"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-sky-500 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 transition-colors"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full mt-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-sky-600 to-teal-500 hover:from-sky-500 hover:to-teal-400 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-sky-600/25 transition-all disabled:opacity-60"
              >
                {busy ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Console</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Fill Button */}
            <div className="mt-5 pt-4 border-t border-slate-800 text-center">
              <button
                type="button"
                onClick={handleQuickFill}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-teal-300 bg-teal-950/60 border border-teal-800/80 hover:bg-teal-900/60 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                Auto-Fill Administrator Credentials
              </button>
              <div className="text-[11px] text-slate-400 mt-2">
                User: <span className="text-slate-300 font-mono">sarvesh</span> · Password:{" "}
                <span className="text-slate-300 font-mono">sarvesh@suyal</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-3 border-t border-slate-900 text-center text-xs text-slate-400">
        GeoHarmonize Platform · Government of India · Department of Land Resources
      </footer>
    </div>
  );
}
