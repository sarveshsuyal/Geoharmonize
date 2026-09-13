import React, { useEffect, useState } from "react";
import api from "../services/api";

export default function ChangeDetectionPage() {
  const [datasets, setDatasets] = useState([]);
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/datasets/").then((res) => setDatasets(res.data.results || res.data));
  }, []);

  async function run() {
    if (!before || !after) return;
    setBusy(true);
    try {
      const res = await api.post("/change-detection/run/", { dataset_before_id: before, dataset_after_id: after });
      setResult(res.data);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-xl font-semibold text-ink-900 mb-1">Change Detection</h1>
      <p className="text-sm text-ink-500 mb-4">Compare two datasets/years and classify feature changes.</p>

      <div className="card p-4 flex items-end gap-4 mb-4">
        <div className="flex-1">
          <label className="block text-xs font-medium text-ink-600 mb-1">Before</label>
          <select className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm" value={before} onChange={(e) => setBefore(e.target.value)}>
            <option value="">Select dataset</option>
            {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-ink-600 mb-1">After</label>
          <select className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm" value={after} onChange={(e) => setAfter(e.target.value)}>
            <option value="">Select dataset</option>
            {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <button onClick={run} disabled={busy} className="btn-primary">{busy ? "Comparing..." : "Compare"}</button>
      </div>

      {result && (
        <div className="card p-4">
          <div className="text-sm font-medium text-ink-800 mb-3">Run #{result.id} — {result.status}</div>
          <div className="grid grid-cols-4 gap-3">
            {Object.entries(result.statistics || {}).map(([k, v]) => (
              <div key={k} className="bg-ink-50 rounded p-3 text-center">
                <div className="text-2xl font-semibold text-ink-900">{v}</div>
                <div className="text-xs text-ink-500 uppercase">{k}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
