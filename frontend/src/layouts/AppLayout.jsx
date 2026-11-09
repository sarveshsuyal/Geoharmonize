import React, { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, Link } from "react-router-dom";
import { useAuth } from "../services/AuthContext.jsx";
import { getApiBaseUrl, checkBackendHealth } from "../services/api.js";
import {
  LayoutDashboard,
  Layers,
  UploadCloud,
  Map as MapIcon,
  GitMerge,
  AlertTriangle,
  ClipboardCheck,
  History,
  FileText,
  Settings as SettingsIcon,
  LogOut,
  Server,
  Activity,
  Menu,
  X,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/datasets", label: "Datasets", icon: Layers },
  { to: "/upload", label: "Upload Data", icon: UploadCloud },
  { to: "/map", label: "GIS Map Viewer", icon: MapIcon },
  { to: "/harmonization", label: "Harmonization", icon: GitMerge },
  { to: "/conflicts", label: "Conflicts", icon: AlertTriangle },
  { to: "/review", label: "Review Queue", icon: ClipboardCheck },
  { to: "/change-detection", label: "Change Detection", icon: History },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings & Cloud", icon: SettingsIcon },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState({ checked: false, ok: false, latency: null });

  // Periodically check backend health
  useEffect(() => {
    let mounted = true;
    async function checkHealth() {
      const res = await checkBackendHealth();
      if (mounted) {
        setHealthStatus({ checked: true, ok: res.ok, latency: res.latency, data: res.data });
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const currentNav = NAV_ITEMS.find((n) => n.to === location.pathname) || { label: "GeoHarmonize" };
  const apiUrl = getApiBaseUrl();
  const isRenderCloud = apiUrl.includes("onrender.com");

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-800">
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-slate-200 flex flex-col transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-auto ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-sky-600 to-teal-400 flex items-center justify-center shadow-md shadow-sky-900/30">
              <MapIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                GeoHarmonize
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-400/30">
                  SIH
                </span>
              </div>
              <div className="text-[11px] text-slate-400 leading-none mt-0.5">
                Land Records Harmonization
              </div>
            </div>
          </div>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Agency Tag */}
        <div className="px-5 py-2.5 bg-slate-950/40 border-b border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-teal-400 shrink-0" />
          <span className="truncate">Dept. of Land Resources · MoRD</span>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-sky-600 text-white shadow-sm shadow-sky-600/30 font-semibold"
                      : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Cloud Status Indicator */}
        <div className="px-4 py-3 mx-3 mb-3 rounded-lg bg-slate-800/70 border border-slate-700/60 text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="text-slate-400 flex items-center gap-1.5 text-[11px]">
              <Server className="w-3 h-3 text-slate-400" />
              Backend Service
            </span>
            <span
              className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.2 rounded-full ${
                healthStatus.ok
                  ? "bg-emerald-500/20 text-emerald-300"
                  : healthStatus.checked
                  ? "bg-rose-500/20 text-rose-300"
                  : "bg-amber-500/20 text-amber-300"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  healthStatus.ok
                    ? "bg-emerald-400 animate-pulse"
                    : healthStatus.checked
                    ? "bg-rose-400"
                    : "bg-amber-400 animate-pulse"
                }`}
              />
              {healthStatus.ok ? "ONLINE" : healthStatus.checked ? "OFFLINE" : "CONNECTING"}
            </span>
          </div>
          <div className="text-[11px] text-slate-300 font-mono truncate" title={apiUrl}>
            {isRenderCloud ? "Render Cloud" : apiUrl.replace(/^https?:\/\//, "")}
          </div>
          {healthStatus.latency !== null && (
            <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
              <span>Latency</span>
              <span>{healthStatus.latency} ms</span>
            </div>
          )}
        </div>

        {/* User Card */}
        <div className="px-4 py-3.5 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-500 to-orange-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
              {user?.first_name?.[0] || user?.username?.[0]?.toUpperCase() || "S"}
              {user?.last_name?.[0] || "S"}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-white truncate">
                {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : user?.username || "Officer"}
              </div>
              <div className="text-[10px] text-slate-400 truncate">
                {user?.role || "ADMIN"} · {user?.designation || "Administrator"}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-1.5 rounded-md text-slate-400 hover:text-rose-300 hover:bg-slate-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-14 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 lg:hidden"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span className="font-semibold text-slate-800 text-base">{currentNav.label}</span>
              <span className="hidden sm:inline text-slate-300">/</span>
              <span className="hidden sm:inline text-xs text-slate-500">
                National Land Records Modernization
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick Status Pill */}
            <Link
              to="/settings"
              className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                healthStatus.ok
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                  : "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  healthStatus.ok ? "bg-emerald-500 animate-pulse" : "bg-amber-500 animate-pulse"
                }`}
              />
              {healthStatus.ok
                ? `${isRenderCloud ? "Render" : "API"} Connected (${healthStatus.latency}ms)`
                : "Checking Cloud API..."}
            </Link>

            {/* View Map Shortcut */}
            {location.pathname !== "/map" && (
              <Link
                to="/map"
                className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
              >
                <MapIcon className="w-3.5 h-3.5 text-sky-600" />
                <span className="hidden md:inline">Open Map</span>
              </Link>
            )}

            {/* Officer Chip */}
            <div className="hidden md:flex items-center gap-2 pl-2 border-l border-slate-200 text-xs text-slate-600">
              <span className="font-medium text-slate-800">
                {user?.username || "sarvesh"}
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-sky-100 text-sky-700">
                {user?.role || "ADMIN"}
              </span>
            </div>
          </div>
        </header>

        {/* Page Body */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
