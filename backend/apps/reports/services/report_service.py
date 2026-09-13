"""
Generates CSV (always) and PDF (if reportlab is available) reports from
actual database records - never synthetic/pre-written content.
"""
import csv
import io


class ReportService:

    def harmonization_summary_csv(self, run) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Run ID", run.id])
        writer.writerow(["Status", run.status])
        for k, v in (run.statistics or {}).items():
            writer.writerow([k, v])
        return buf.getvalue()

    def conflict_report_csv(self, conflicts_qs) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Type", "Severity", "Status", "Confidence", "Description", "Created"])
        for c in conflicts_qs:
            writer.writerow([c.id, c.conflict_type, c.severity, c.status, c.confidence, c.description, c.created_at])
        return buf.getvalue()

    def dataset_validation_report_csv(self, datasets_qs) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Name", "Type", "Status", "CRS", "Feature Count", "Errors"])
        for d in datasets_qs:
            writer.writerow([d.id, d.name, d.dataset_type, d.processing_status, d.original_crs,
                              d.feature_count, d.error_message])
        return buf.getvalue()

    def parcel_matching_report_csv(self, matches_qs) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Source Parcel", "Target Parcel", "Overlap", "Area Similarity",
                          "Centroid Distance (m)", "Shape Similarity", "Confidence", "Status"])
        for m in matches_qs:
            writer.writerow([m.source_parcel.parcel_id, m.target_parcel.parcel_id,
                              round(m.overlap_ratio, 3), round(m.area_similarity, 3),
                              round(m.centroid_distance_m, 2), round(m.shape_similarity, 3),
                              m.overall_confidence, m.status])
        return buf.getvalue()

    def change_detection_report_csv(self, run) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Feature Kind", "Change Type", "IoU"])
        for f in run.features.all():
            writer.writerow([f.feature_kind, f.change_type, f.iou])
        return buf.getvalue()

    def to_pdf(self, title: str, csv_text: str) -> bytes:
        """Best-effort PDF export. Requires reportlab (see requirements.txt);
        if unavailable, callers should fall back to CSV and inform the user."""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, title)
        y -= 30
        c.setFont("Helvetica", 8)
        for line in csv_text.splitlines():
            if y < 40:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 8)
            c.drawString(40, y, line[:130])
            y -= 12
        c.save()
        return buf.getvalue()
