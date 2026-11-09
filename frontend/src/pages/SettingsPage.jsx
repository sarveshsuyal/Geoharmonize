import React, { useState, useEffect } from "react";
import { useAuth } from "../services/AuthContext.jsx";
import { getApiBaseUrl, setApiBaseUrl, checkBackendHealth } from "../services/api.js";
import {
  Server,
  Database,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Shield,
  Layers,
  Sliders,
  ExternalLink,
  Save,
  Cpu,
  User,
  MapPin,
  FileCode,
} from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();

  const [apiUrl, setApiUrl] = useState(getApiBaseUrl());
  const [inputUrl, setInputUrl] = useState(getApiBaseUrl());
  const [testing, setTesting] = useState(false);
  const [healthResult, setHealthResult] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  async function runHealthCheck(urlToTest = null) {
    setTesting(true);
    const res = await checkBackendHealth(urlToTest || apiUrl);
    setHealthResult(res);
    setTesting(false);
  }

  useEffect(() => {
    runHealthCheck();
  }, [apiUrl]);

  function handleSaveUrl(e) {
    e.preventDefault();
    setApiBaseUrl(inputUrl);
    setApiUrl(getApiBaseUrl());
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
    runHealthCheck(getApiBaseUrl());
  }

  function handlePreset(url) {
    setInputUrl(url);
    setApiBaseUrl(url);
    setApiUrl(url);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
    runHealthCheck(url);
  }

  const isRenderCloud = apiUrl.includes("onrender.com");

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">System Settings & Cloud</h1>
        <p className="text-xs text-slate-500 mt-1">
          Manage API connectivity, Render cloud deployment, Cadastral projection parameters, and user permissions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Backend & Render Connection Manager */}
        <div className="lg:col-span-2 space-y-6">
          {/* API Connection Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-sky-600" />
                <h2 className="text-base font-bold text-slate-900">Backend API Connection</h2>
              </div>
              <button
                onClick={() => runHealthCheck()}
                disabled={testing}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testing ? "animate-spin" : ""}`} />
                <span>Test Ping</span>
              </button>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              Connect this frontend console to your deployed Render web service or a local Docker environment.
            </p>

            {/* Presets */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold text-slate-400">Presets:</span>
              <button
                type="button"
                onClick={() => handlePreset("http://localhost:8000/api")}
                className="px-2.5 py-1 text-xs rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors font-mono"
              >
                Local Docker (http://localhost:8000/api)
              </button>
              <button
                type="button"
                onClick={() => handlePreset("https://geoharmonize-backend.onrender.com/api")}
                className="px-2.5 py-1 text-xs rounded-md bg-sky-50 hover:bg-sky-100 text-sky-700 transition-colors font-mono"
              >
                Render Cloud (geoharmonize-backend)
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSaveUrl} className="space-y-3 pt-1">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Active API Endpoint URL
                </label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={inputUrl}
                    onChange={(e) => setInputUrl(e.target.value)}
                    className="flex-1 bg-slate-50 border border-slate-300 focus:border-sky-500 rounded-lg px-3 py-2 text-xs font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    placeholder="https://your-service.onrender.com/api"
                    required
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs rounded-lg flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Apply</span>
                  </button>
                </div>
              </div>
            </form>

            {saveSuccess && (
              <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>API Endpoint updated and saved to local storage!</span>
              </div>
            )}

            {/* Health Diagnostics Output */}
            {healthResult && (
              <div
                className={`p-4 rounded-xl border text-xs space-y-2 ${
                  healthResult.ok
                    ? "bg-emerald-50/60 border-emerald-200 text-emerald-950"
                    : "bg-rose-50/60 border-rose-200 text-rose-950"
                }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <div className="flex items-center gap-1.5">
                    {healthResult.ok ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-rose-600" />
                    )}
                    <span>
                      {healthResult.ok ? "Backend Operational & Verified" : "Backend Health Check Failed"}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-white/80 border border-current">
                    Latency: {healthResult.latency}ms
                  </span>
                </div>

                {healthResult.ok && healthResult.data && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-emerald-200/60 text-[11px]">
                    <div>
                      <span className="text-emerald-700 block">Service:</span>
                      <span className="font-semibold">{healthResult.data.service}</span>
                    </div>
                    <div>
                      <span className="text-emerald-700 block">Platform:</span>
                      <span className="font-semibold">{healthResult.data.platform || "Docker"}</span>
                    </div>
                    <div>
                      <span className="text-emerald-700 block">PostGIS Status:</span>
                      <span className="font-semibold text-emerald-700">
                        {healthResult.data.database?.postgis_ready ? "Active & Installed" : "Standard DB"}
                      </span>
                    </div>
                  </div>
                )}

                {!healthResult.ok && (
                  <div className="text-[11px] text-rose-700 pt-1 leading-relaxed">
                    Error details: {healthResult.error || "Connection timed out or network error."}
                    {isRenderCloud && (
                      <div className="mt-1 font-semibold">
                        Note: Free-tier Render instances sleep when inactive. Please allow ~40s for initial cold start.
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Render Cloud Deployment Readiness Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-teal-600" />
              <h2 className="text-base font-bold text-slate-900">Render Cloud Deployment Package</h2>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              GeoHarmonize is packaged with complete Infrastructure-as-Code files for zero-friction deployment on Render:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <div className="font-bold text-slate-800 flex items-center gap-1.5">
                  <FileCode className="w-4 h-4 text-sky-600" />
                  <code>render.yaml</code> (Blueprint)
                </div>
                <p className="text-slate-500 text-[11px]">
                  Provisions PostgreSQL 16 database, Docker Web Service with GDAL C-libraries, and Static Frontend automatically.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <div className="font-bold text-slate-800 flex items-center gap-1.5">
                  <FileCode className="w-4 h-4 text-sky-600" />
                  <code>start.sh</code> & <code>Dockerfile</code>
                </div>
                <p className="text-slate-500 text-[11px]">
                  Auto-enables PostGIS, runs Django migrations, collects static assets, creates admin user, and binds to dynamic <code>$PORT</code>.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-sky-50 border border-sky-100 text-xs text-sky-900 leading-relaxed">
              <strong>Need step-by-step instructions?</strong> See the complete guide in{" "}
              <code className="bg-sky-100 px-1 py-0.5 rounded font-mono">DEPLOY_RENDER.md</code> in the repository root.
            </div>
          </div>

          {/* Algorithmic Weighting & Parameters */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                Spatial Matching & Confidence Parameters
              </h2>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              These weights govern the multi-factor IoU and confidence scoring algorithm implemented in{" "}
              <code>apps/harmonization/services/matching_service.py</code>.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <span className="text-[11px] text-slate-500 block">Overlap (IoU)</span>
                <span className="text-sm font-bold text-slate-800">35%</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <span className="text-[11px] text-slate-500 block">Centroid Dist</span>
                <span className="text-sm font-bold text-slate-800">20%</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <span className="text-[11px] text-slate-500 block">Area Ratio</span>
                <span className="text-sm font-bold text-slate-800">20%</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <span className="text-[11px] text-slate-500 block">Shape Compactness</span>
                <span className="text-sm font-bold text-slate-800">15%</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <span className="text-[11px] text-slate-500 block">Boundary Hausdorff</span>
                <span className="text-sm font-bold text-slate-800">10%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: User Profile & Cadastral Info */}
        <div className="space-y-6">
          {/* User Profile Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <User className="w-5 h-5 text-slate-700" />
              <h2 className="text-base font-bold text-slate-900">Officer Profile</h2>
            </div>

            <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
              <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-sky-600 to-teal-400 text-white font-bold text-base flex items-center justify-center shadow">
                {user?.first_name?.[0] || user?.username?.[0]?.toUpperCase() || "S"}
                {user?.last_name?.[0] || "S"}
              </div>
              <div>
                <div className="font-bold text-slate-900 text-sm">
                  {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : user?.username || "Sarvesh Suyal"}
                </div>
                <div className="text-xs text-slate-500">{user?.email || "sarvesh112k@gmail.com"}</div>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Username</span>
                <span className="font-mono text-slate-800">{user?.username || "sarvesh"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Assigned Role</span>
                <span className="font-semibold text-sky-700 px-2 py-0.5 rounded bg-sky-50 border border-sky-200 text-[10px]">
                  {user?.role || "ADMIN"}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Designation</span>
                <span className="font-medium text-slate-800">{user?.designation || "Administrator"}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Organization</span>
                <span className="font-medium text-slate-800 text-right">
                  {user?.organization || "Department of Land Resources"}
                </span>
              </div>
            </div>
          </div>

          {/* Cadastral Coordinate Reference System */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">Project Target CRS</h2>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 space-y-1">
              <div className="font-bold text-sky-700">EPSG:32644</div>
              <div className="text-[11px] text-slate-500">WGS 84 / UTM Zone 44N (Northern India)</div>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              All ingested cadastral geometries are transformed to UTM Zone 44N to allow high-accuracy metric
              distance calculations (meters) for areas, centroids, and overlaps.
            </p>
          </div>

          {/* Confidence Tiers */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-600" />
              <h2 className="text-base font-bold text-slate-900">Confidence Tiers</h2>
            </div>
            <div className="space-y-2 text-xs">
              <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200 flex justify-between items-center text-emerald-900">
                <span className="font-semibold">HIGH CONFIDENCE</span>
                <span className="font-bold">≥ 85%</span>
              </div>
              <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 flex justify-between items-center text-amber-900">
                <span className="font-semibold">MEDIUM (Officer Review)</span>
                <span className="font-bold">65% – 84%</span>
              </div>
              <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 flex justify-between items-center text-rose-900">
                <span className="font-semibold">LOW (Field Survey Req.)</span>
                <span className="font-bold">&lt; 65%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
