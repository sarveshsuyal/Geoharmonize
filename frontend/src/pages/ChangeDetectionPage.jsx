import React, { useEffect, useState } from "react";
import api from "../services/api";
import {
  History,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Layers,
  Sparkles,
  GitCompare,
} from "lucide-react";

export default function ChangeDetectionPage() {
  const [datasets, setDatasets] = useState([]);
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/datasets/").then((res) => setDatasets(res.data.results || res.data));
  }, []);

  async function run() {
    if (!before || !after) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post("/change-detection/run/", {
        dataset_before_id: before,
        dataset_after_id: after,
      });
      setResult(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Change detection analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Temporal Change Detection</h1>
        <p className="text-xs text-slate-500 mt-1">
          Perform multi-temporal geometric comparison between baseline cadastral records and current drone/satellite surveys.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <GitCompare className="w-5 h-5 text-sky-600" />
          <h2 className="text-base font-bold text-slate-900">Select Epochs for Comparison</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Baseline Layer (Before / Epoch T1)
            </label>
            <select
              className="w-full border border-slate-300 focus:border-sky-500 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
              value={before}
              onChange={(e) => setBefore(e.target.value)}
            >
              <option value="">Select baseline dataset...</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.dataset_type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Follow-up Layer (After / Epoch T2)
            </label>
            <select
              className="w-full border border-slate-300 focus:border-sky-500 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
              value={after}
              onChange={(e) => setAfter(e.target.value)}
            >
              <option value="">Select current dataset...</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.dataset_type})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={run}
            disabled={busy || !before || !after}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs shadow-sm transition-colors disabled:opacity-50"
          >
            {busy ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Computing Differences...</span>
              </>
            ) : (
              <>
                <History className="w-4 h-4" />
                <span>Compute Temporal Changes</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {result && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <span className="font-bold text-slate-900 text-base">
                Temporal Change Run #{result.id} — {result.status}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(result.statistics || {}).map(([key, val]) => (
              <div key={key} className="bg-slate-50 rounded-xl p-3.5 border border-slate-100 text-center">
                <div className="text-2xl font-bold text-slate-900">{val}</div>
                <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mt-1">
                  {key.replace(/_/g, " ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
