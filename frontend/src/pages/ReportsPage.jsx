import React, { useState } from "react";
import { getApiBaseUrl } from "../services/api.js";
import {
  FileText,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Clock,
  ShieldCheck,
} from "lucide-react";

const REPORTS = [
  {
    id: "conflicts",
    title: "Comprehensive Conflict Audit Report",
    format: "CSV",
    description:
      "All active and resolved cadastral boundary discrepancies, area mismatches, building encroachments, and officer resolutions.",
    path: "/reports/conflicts/",
    icon: AlertTriangle,
    badgeColor: "bg-rose-50 text-rose-700 border-rose-200",
  },
  {
    id: "dataset-validation",
    title: "Dataset Ingestion & CRS Validation Report",
    format: "CSV",
    description:
      "Full inventory of uploaded layers, original CRS detection results, coordinate bounds, topology checks, and feature counts.",
    path: "/reports/dataset-validation/",
    icon: ShieldCheck,
    badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  {
    id: "parcel-matching",
    title: "Spatial IoU & Parcel Matching Reconciliation Report",
    format: "CSV",
    description:
      "Pairwise spatial matching metrics (IoU, centroid decay, Hausdorff distance, shape compactness) and multi-factor confidence scores.",
    path: "/reports/parcel-matching/",
    icon: FileSpreadsheet,
    badgeColor: "bg-sky-50 text-sky-700 border-sky-200",
  },
];

export default function ReportsPage() {
  const [downloading, setDownloading] = useState(null);

  function handleDownload(report) {
    const baseURL = getApiBaseUrl();
    const token = localStorage.getItem("gh_access_token");
    setDownloading(report.id);

    fetch(`${baseURL}${report.path}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Download failed");
        return res.blob();
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const filename = `${report.id}_report_${new Date().toISOString().slice(0, 10)}.csv`;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch((err) => {
        alert("Failed to generate report. Ensure backend is running.");
      })
      .finally(() => setDownloading(null));
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Executive Reports & Data Exports</h1>
        <p className="text-xs text-slate-500 mt-1">
          Generate auditable reports computed directly from the live PostgreSQL/PostGIS database state.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {REPORTS.map((r) => {
          const Icon = r.icon;
          const isBusy = downloading === r.id;
          return (
            <div
              key={r.id}
              className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center text-slate-700">
                    <Icon className="w-5 h-5 text-sky-600" />
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${r.badgeColor}`}
                  >
                    {r.format}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900">{r.title}</h3>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">{r.description}</p>
                </div>
              </div>

              <div className="pt-4 mt-4 border-t border-slate-100">
                <button
                  onClick={() => handleDownload(r)}
                  disabled={isBusy}
                  className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-60"
                >
                  {isBusy ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Generating Report...</span>
                    </>
                  ) : (
                    <>
                      <Download className="w-3.5 h-3.5" />
                      <span>Download {r.format}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Audit Banner */}
      <div className="p-4 rounded-xl bg-slate-100/70 border border-slate-200 text-xs text-slate-600 leading-relaxed flex items-center gap-3">
        <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0" />
        <div>
          <strong>Statutory Compliance & Traceability</strong>: Every generated export includes SHA-256
          source hashes, timestamped officer action IDs, and geometry reconciliation metrics satisfying
          Ministry of Rural Development audit standards.
        </div>
      </div>
    </div>
  );
}
