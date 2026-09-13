import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../services/AuthContext.jsx";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/datasets", label: "Datasets" },
  { to: "/upload", label: "Upload Data" },
  { to: "/map", label: "GIS Map" },
  { to: "/harmonization", label: "Harmonization" },
  { to: "/conflicts", label: "Conflicts" },
  { to: "/review", label: "Review Queue" },
  { to: "/change-detection", label: "Change Detection" },
  { to: "/reports", label: "Reports" },
  { to: "/settings", label: "Settings" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-ink-900 text-ink-100 flex flex-col">
        <div className="px-4 py-5 border-b border-white/10">
          <div className="text-lg font-semibold tracking-tight text-white">GeoHarmonize</div>
          <div className="text-[11px] text-ink-200/70 leading-snug mt-1">
            AI-Powered Multi-Source Geospatial Land Record Harmonization Platform
          </div>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-600 text-white" : "text-ink-200 hover:bg-white/5"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-white/10 text-xs text-ink-200/80">
          <div className="font-medium text-ink-100">{user?.username}</div>
          <div className="mb-2">{user?.role}</div>
          <button onClick={logout} className="text-brand-500 hover:text-brand-400">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 bg-ink-50">
        <Outlet />
      </main>
    </div>
  );
}
