"""
Candidate parcel boundary detection from imagery. Distinct from building
detection: looks for larger enclosed regions (field/plot boundaries) rather
than compact building footprints. Uses the same classical-CV building blocks
with different filtering thresholds - still explicitly COMPUTER_VISION, not ML.
"""
import time


class ParcelBoundaryDetector:
    model_name = "OpenCV Classical Pipeline (parcel mode)"
    model_version = "1.0-mvp"
    method_category = "COMPUTER_VISION"

    MIN_PARCEL_AREA_PX = 2000

    def detect(self, dataset) -> dict:
        import cv2
        import numpy as np
        from apps.geospatial.services.raster_service import RasterService

        start = time.time()
        rs = RasterService()
        arr, transform, crs = rs.read_as_array(dataset.file.path)
        img = arr.mean(axis=0).astype(np.uint8) if arr.ndim == 3 else arr.astype(np.uint8)

        edges = cv2.Canny(cv2.GaussianBlur(img, (7, 7), 0), 30, 100)
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
        contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for cnt in contours:
            area_px = cv2.contourArea(cnt)
            if area_px < self.MIN_PARCEL_AREA_PX:
                continue
            epsilon = 0.01 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            pixel_coords = [(int(p[0][0]), int(p[0][1])) for p in approx]
            polygon = rs.pixel_polygon_to_map_polygon(transform, pixel_coords)
            if polygon and polygon.is_valid and not polygon.is_empty:
                candidates.append(polygon)

        return {
            "model": self.model_name, "version": self.model_version,
            "method_category": self.method_category,
            "candidate_count": len(candidates),
            "processing_time_ms": int((time.time() - start) * 1000),
            "geometries_wkt": [c.wkt for c in candidates],
        }
