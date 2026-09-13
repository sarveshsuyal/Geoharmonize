import React, { useEffect, useState } from "react";
import api from "../services/api";

function StatCard({ label, value, tone = "default" }) {
  const toneClass = {
    default: "text-ink-900",
    high: "text-status-high",
    medium: "text-status-medium",
    low: "text-status-low",
  }[tone];
  return (
    <div className="card p-4">
      <div className="text-xs text-ink-500 mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${toneClass}`}>{value ?? "—"}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoResult, setDemoResult] = useState(null);

  function loadStats() {
    api
      .get("/dashboard/stats/")
      .then((res) => setStats(res.data))
      .catch(() => setError("Could not load dashboard statistics from the backend."));
  }

  useEffect(loadStats, []);

  async function runDemo() {
    setDemoRunning(true);
    setDemoResult(null);
    try {
      const res = await api.post("/demo/run/");
      setDemoResult(res.data);
      loadStats();
    } catch (e) {
      setError(e?.response?.data?.message || "Demo run failed. Check backend logs.");
    } finally {
      setDemoRunning(false);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">Dashboard</h1>
          <p className="text-sm text-ink-500 mt-1">
            Live statistics computed from the harmonized database — nothing on this page is hard-coded.
          </p>
        </div>
        <button onClick={runDemo} disabled={demoRunning} className="btn-primary">
          {demoRunning ? "Running demo..." : "Run Demo"}
        </button>
      </div>

      {error && <div className="card p-3 text-sm text-status-low bg-red-50 border-red-200">{error}</div>}

      {!stats ? (
        <div className="text-sm text-ink-500">Loading statistics...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Datasets" value={stats.total_datasets} />
            <StatCard label="Total Parcels" value={stats.total_parcels} />
            <StatCard label="Matched Parcels" value={stats.matched_parcels} tone="high" />
            <StatCard label="Unmatched Parcels" value={stats.unmatched_parcels} tone="medium" />
            <StatCard label="Conflicts" value={stats.conflicts} tone="low" />
            <StatCard label="Resolved Conflicts" value={stats.resolved_conflicts} tone="high" />
            <StatCard label="Pending Reviews" value={stats.pending_reviews} tone="medium" />
            <StatCard label="Average Confidence" value={stats.average_confidence ? `${stats.average_confidence}%` : "—"} />
          </div>

          {stats.latest_run && (
            <div className="card p-4">
              <div className="text-sm font-medium text-ink-800 mb-2">
                Latest Harmonization Run #{stats.latest_run.id} — {stats.latest_run.status}
              </div>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-3 text-xs">
                {Object.entries(stats.latest_run.statistics || {}).map(([k, v]) => (
                  <div key={k} className="bg-ink-50 rounded px-2 py-1.5">
                    <div className="text-ink-500">{k.replace(/_/g, " ")}</div>
                    <div className="font-semibold text-ink-800">{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {demoResult && (
        <div className="card p-4">
          <div className="text-sm font-medium text-ink-800 mb-2">Demo run complete</div>
          <div className="text-xs text-ink-500 mb-2">
            Generated {demoResult.datasets.length} datasets, ran harmonization run #
            {demoResult.harmonization_run_id}. Statistics below were computed by the real matching/
            conflict-detection pipeline against the synthetic data.
          </div>
          <pre className="text-xs bg-ink-900 text-ink-100 rounded p-3 overflow-x-auto">
            {JSON.stringify(demoResult.statistics, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
