import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import {
  Layers,
  Map as MapIcon,
  CheckCircle2,
  AlertTriangle,
  Play,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  RefreshCw,
  GitMerge,
  Clock,
  Sparkles,
  Database,
  Compass,
} from "lucide-react";

const PIPELINE_STEPS = [
  { id: 1, name: "Ingestion", desc: "GeoJSON, SHP, TIFF, KML" },
  { id: 2, name: "CRS Normalization", desc: "Standardize to EPSG:32644" },
  { id: 3, name: "Geometry Validation", desc: "ST_IsValid & Auto-Repair" },
  { id: 4, name: "Spatial Matching", desc: "IoU, Centroid, Shape similarity" },
  { id: 5, name: "Attribute Mapping", desc: "Khasra, Survey, Owner linking" },
  { id: 6, name: "Topology Check", desc: "Overlap & Sliver prevention" },
  { id: 7, name: "Conflict Detection", desc: "Boundary & Encroachment flags" },
  { id: 8, name: "Confidence Scoring", desc: "0-100% Measured Score" },
  { id: 9, name: "Unified Layer", desc: "Harmonized Cadastral Output" },
];

function StatCard({ label, value, subtext, icon: Icon, tone = "default" }) {
  const styles = {
    default: {
      bg: "bg-white",
      border: "border-slate-200",
      iconBg: "bg-slate-100 text-slate-700",
      valColor: "text-slate-900",
    },
    success: {
      bg: "bg-white",
      border: "border-emerald-200",
      iconBg: "bg-emerald-50 text-emerald-600",
      valColor: "text-emerald-700",
    },
    warning: {
      bg: "bg-white",
      border: "border-amber-200",
      iconBg: "bg-amber-50 text-amber-600",
      valColor: "text-amber-700",
    },
    danger: {
      bg: "bg-white",
      border: "border-rose-200",
      iconBg: "bg-rose-50 text-rose-600",
      valColor: "text-rose-700",
    },
    brand: {
      bg: "bg-white",
      border: "border-sky-200",
      iconBg: "bg-sky-50 text-sky-600",
      valColor: "text-sky-700",
    },
  }[tone];

  return (
    <div className={`p-4 rounded-xl border ${styles.border} ${styles.bg} shadow-sm transition-all hover:shadow-md`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${styles.iconBg}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className={`text-2xl font-bold tracking-tight ${styles.valColor}`}>{value ?? "—"}</div>
      {subtext && <div className="text-[11px] text-slate-400 mt-1">{subtext}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoResult, setDemoResult] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  function loadStats() {
    setRefreshing(true);
    api
      .get("/dashboard/stats/")
      .then((res) => {
        setStats(res.data);
        setError("");
      })
      .catch((err) => {
        setError(
          err.response?.data?.detail || "Could not load dashboard statistics. Verify backend is running."
        );
      })
      .finally(() => setRefreshing(false));
  }

  useEffect(loadStats, []);

  async function runDemo() {
    setDemoRunning(true);
    setDemoResult(null);
    setError("");
    try {
      const res = await api.post("/demo/run/");
      setDemoResult(res.data);
      loadStats();
    } catch (e) {
      setError(e?.response?.data?.message || "Demo execution failed. Check backend logs.");
    } finally {
      setDemoRunning(false);
    }
  }

  const matchRate =
    stats?.total_parcels > 0
      ? Math.round((stats.matched_parcels / stats.total_parcels) * 100)
      : null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner / Welcome */}
      <div className="bg-gradient-to-r from-slate-900 via-sky-950 to-slate-900 rounded-2xl p-6 text-white shadow-xl flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-500/20 text-sky-300 border border-sky-400/30">
              Department of Land Resources · MoRD
            </span>
            <span className="text-xs text-slate-400">SIH26013 Prototype</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Land Records Harmonization Console
          </h1>
          <p className="text-sm text-slate-300 max-w-2xl mt-1 leading-relaxed">
            Multi-source spatial reconciliation engine unifying Cadastral Maps, High-Res Drone
            Imagery, Revenue Titles, and Municipal GIS into a single verified land layer.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            onClick={runDemo}
            disabled={demoRunning}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-teal-400 hover:from-sky-400 hover:to-teal-300 text-slate-950 font-semibold text-sm shadow-lg shadow-sky-500/20 transition-all disabled:opacity-60"
          >
            {demoRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-slate-950" />
                <span>Run Cadastral Demo</span>
              </>
            )}
          </button>

          <Link
            to="/map"
            className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium border border-slate-700 transition-colors"
          >
            <MapIcon className="w-4 h-4 text-sky-400" />
            <span>Open GIS Map</span>
          </Link>

          <button
            onClick={loadStats}
            disabled={refreshing}
            title="Refresh stats"
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-700 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={loadStats} className="text-xs font-semibold underline hover:text-rose-900">
            Retry
          </button>
        </div>
      )}

      {/* Demo Result Toast/Card */}
      {demoResult && (
        <div className="p-5 rounded-2xl bg-gradient-to-r from-teal-50 to-sky-50 border border-teal-200 text-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-teal-600" />
              <span className="font-bold text-teal-900 text-base">
                Cadastral Demo Pipeline Executed Successfully!
              </span>
            </div>
            <Link
              to="/map"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm"
            >
              <span>View On Map</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Multi-source test datasets (Cadastral Survey vs Drone Imagery) have been ingested into
            PostGIS, projected to EPSG:32644, matched with spatial IoU, and confidence-scored.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100">
              <span className="text-slate-500 block text-[11px]">Features Ingested</span>
              <span className="font-bold text-slate-800 text-sm">
                {demoResult.features_ingested || demoResult.parcels_created || "Loaded"}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100">
              <span className="text-slate-500 block text-[11px]">Matched Pairs</span>
              <span className="font-bold text-emerald-700 text-sm">
                {demoResult.matched_pairs || "Auto-detected"}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100">
              <span className="text-slate-500 block text-[11px]">Detected Conflicts</span>
              <span className="font-bold text-amber-700 text-sm">
                {demoResult.conflicts_flagged || "Flagged for review"}
              </span>
            </div>
            <div className="bg-white/80 rounded-lg p-2 border border-teal-100">
              <span className="text-slate-500 block text-[11px]">Study Area</span>
              <span className="font-bold text-slate-800 text-sm">Northern India (UTM 44N)</span>
            </div>
          </div>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Datasets Ingested"
          value={stats?.total_datasets}
          subtext="Cadastral, Drone, Satellite layers"
          icon={Layers}
          tone="brand"
        />
        <StatCard
          label="Total Land Parcels"
          value={stats?.total_parcels}
          subtext={matchRate !== null ? `${matchRate}% matched rate` : "Across all active datasets"}
          icon={Database}
          tone="default"
        />
        <StatCard
          label="Matched Parcels"
          value={stats?.matched_parcels}
          subtext="IoU & Attribute verified"
          icon={CheckCircle2}
          tone="success"
        />
        <StatCard
          label="Average Match Confidence"
          value={stats?.average_confidence ? `${stats.average_confidence}%` : "—"}
          subtext="Weighted metric across 5 factors"
          icon={TrendingUp}
          tone="brand"
        />
        <StatCard
          label="Pending Review Queue"
          value={stats?.pending_reviews}
          subtext="Requires GIS Officer sign-off"
          icon={Clock}
          tone="warning"
        />
        <StatCard
          label="Detected Conflicts"
          value={stats?.conflicts}
          subtext="Encroachments & discrepancies"
          icon={AlertTriangle}
          tone="danger"
        />
        <StatCard
          label="Resolved Conflicts"
          value={stats?.resolved_conflicts}
          subtext="With recorded audit history"
          icon={ShieldCheck}
          tone="success"
        />
        <StatCard
          label="Unmatched Parcels"
          value={stats?.unmatched_parcels}
          subtext="Gaps flagged for field survey"
          icon={GitMerge}
          tone="warning"
        />
      </div>

      {/* Harmonization Pipeline Visualizer */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              9-Stage Automated Harmonization Pipeline
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic, auditable pipeline executed for every ingestion and reconciliation run.
            </p>
          </div>
          <Link
            to="/harmonization"
            className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
          >
            <span>Run Pipeline</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 gap-2">
          {PIPELINE_STEPS.map((step) => (
            <div
              key={step.id}
              className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex flex-col justify-between hover:border-sky-300 transition-colors"
            >
              <div>
                <div className="text-[10px] font-bold text-sky-600 mb-1">STEP 0{step.id}</div>
                <div className="text-xs font-semibold text-slate-800 leading-tight">
                  {step.name}
                </div>
              </div>
              <div className="text-[10px] text-slate-400 mt-2 leading-tight">{step.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Latest Run & Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Latest Harmonization Run Details */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-500" />
              Latest Harmonization Run Status
            </h3>
            {stats?.latest_run && (
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                  stats.latest_run.status === "COMPLETED"
                    ? "bg-emerald-100 text-emerald-800"
                    : stats.latest_run.status === "RUNNING"
                    ? "bg-sky-100 text-sky-800 animate-pulse"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                Run #{stats.latest_run.id} · {stats.latest_run.status}
              </span>
            )}
          </div>

          {!stats?.latest_run ? (
            <div className="text-center py-8 text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              No harmonization runs recorded yet. Click{" "}
              <button onClick={runDemo} className="text-sky-600 font-semibold underline">
                Run Cadastral Demo
              </button>{" "}
              or upload datasets to start.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                {Object.entries(stats.latest_run.statistics || {}).map(([key, val]) => (
                  <div key={key} className="bg-slate-50 rounded-lg p-2.5 border border-slate-100">
                    <div className="text-[11px] text-slate-500 capitalize">
                      {key.replace(/_/g, " ")}
                    </div>
                    <div className="text-sm font-bold text-slate-800 mt-0.5">{val}</div>
                  </div>
                ))}
              </div>
              <div className="flex justify-end">
                <Link
                  to="/harmonization"
                  className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
                >
                  <span>View Run History & Export GeoJSON</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Quick Launchpad */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Compass className="w-4 h-4 text-sky-600" />
            Quick Navigation
          </h3>
          <div className="space-y-2">
            <Link
              to="/upload"
              className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors"
            >
              <span>Upload New Cadastral Dataset</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
            <Link
              to="/conflicts"
              className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors"
            >
              <span>Inspect Boundary Conflicts</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
            <Link
              to="/review"
              className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors"
            >
              <span>Officer Review Queue</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
            <Link
              to="/reports"
              className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors"
            >
              <span>Download Executive Reports</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
