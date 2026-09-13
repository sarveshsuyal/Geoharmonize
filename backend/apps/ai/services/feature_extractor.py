"""
Feature extraction abstraction for aerial/drone/satellite imagery.

IMPORTANT DISTINCTION (per problem statement - do not blur these):

  COMPUTER VISION (what OpenCVFeatureExtractor actually does):
    Classical image-processing algorithms (edge detection, thresholding,
    morphology, contour tracing) that find candidate shapes in pixels.
    These are NOT learned from data and NOT "AI" in the ML sense - they are
    deterministic, tunable, explainable pipelines.

  MACHINE LEARNING (what MLFeatureExtractor WOULD do - not implemented in
    this MVP, only stubbed):
    A trained segmentation/detection model (e.g. a CNN) that has learned to
    recognize buildings/parcels/roads from labeled training imagery. Requires
    training data and a model file; not fabricated here.

  GEOSPATIAL ALGORITHMS:
    CRS transforms, spatial joins, topology checks, IoU - deterministic
    math over coordinates, unrelated to pixels.

The UI must always show which of these produced a given result, plus a real
confidence score and real processing time - never fabricated.
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class ExtractedFeature:
    geometry: object          # shapely Polygon/LineString in pixel space (caller georeferences)
    confidence: float         # 0-100, derived from a measurable proxy (see subclasses)
    feature_type: str         # e.g. "BUILDING_CANDIDATE"
    method: str                # e.g. "CANNY_EDGE+CONTOUR"


@dataclass
class ExtractionResult:
    features: List[ExtractedFeature]
    model_name: str
    model_version: str
    method_category: str      # "COMPUTER_VISION" | "MACHINE_LEARNING"
    processing_time_ms: int


class BaseFeatureExtractor(ABC):
    model_name: str = "unset"
    model_version: str = "0.0"
    method_category: str = "unset"

    @abstractmethod
    def extract(self, dataset) -> dict:
        """dataset: apps.datasets.models.Dataset (raster). Returns a JSON-serializable
        summary and persists ExtractedFeature results as Building rows with
        detection_method=CV_DETECTED (or a future ML equivalent)."""
        raise NotImplementedError


class OpenCVFeatureExtractor(BaseFeatureExtractor):
    """
    Practical, classical CV pipeline for candidate building-footprint detection
    from orthorectified/drone imagery:
      1. Grayscale + Gaussian blur (denoise)
      2. Canny edge detection
      3. Morphological closing (join broken edges)
      4. Contour detection
      5. Polygon approximation + area/aspect-ratio filtering (reject noise)
      6. Pixel polygons -> map polygons via the raster's affine transform

    This is intentionally simple and explicitly labeled as classical CV, not ML.
    """
    model_name = "OpenCV Classical Pipeline"
    model_version = "1.0-mvp"
    method_category = "COMPUTER_VISION"

    MIN_CONTOUR_AREA_PX = 150   # reject tiny noise contours
    MAX_ASPECT_RATIO = 8.0      # reject implausibly thin slivers as buildings

    def extract(self, dataset) -> dict:
        import cv2
        import numpy as np

        from apps.geospatial.services.raster_service import RasterService

        start = time.time()
        raster_service = RasterService()
        arr, transform, crs = raster_service.read_as_array(dataset.file.path)

        # Normalize to single-band 8-bit grayscale for classical CV ops.
        if arr.ndim == 3:
            img = arr.mean(axis=0).astype(np.uint8)
        else:
            img = arr.astype(np.uint8)

        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        features = []
        for cnt in contours:
            area_px = cv2.contourArea(cnt)
            if area_px < self.MIN_CONTOUR_AREA_PX:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = max(w, h) / max(1, min(w, h))
            if aspect_ratio > self.MAX_ASPECT_RATIO:
                continue

            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            pixel_coords = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
            if len(pixel_coords) < 3:
                continue

            map_polygon = raster_service.pixel_polygon_to_map_polygon(transform, pixel_coords)
            if map_polygon is None or not map_polygon.is_valid or map_polygon.is_empty:
                continue

            # Confidence proxy: how close the contour is to its own convex hull
            # (a real, measurable rectilinearity signal for building-like shapes),
            # NOT a fabricated number.
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull) or 1
            solidity = area_px / hull_area
            confidence = round(min(95.0, solidity * 100), 1)  # capped - classical CV, not a trained detector

            features.append(ExtractedFeature(
                geometry=map_polygon, confidence=confidence,
                feature_type="BUILDING_CANDIDATE", method="CANNY_EDGE+CONTOUR+SOLIDITY",
            ))

        self._persist(dataset, features, transform)

        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "model": self.model_name,
            "version": self.model_version,
            "method_category": self.method_category,
            "candidate_count": len(features),
            "processing_time_ms": elapsed_ms,
            "note": "Classical computer-vision contour detection. Not a trained ML model - "
                    "candidates require officer review before being treated as authoritative footprints.",
        }

    def _persist(self, dataset, features: List[ExtractedFeature], transform):
        from django.contrib.gis.geos import GEOSGeometry
        from apps.parcels.models import Building

        srid = 4326
        try:
            if hasattr(dataset, "target_crs") and dataset.target_crs:
                srid = int(dataset.target_crs.split(":")[-1])
        except (ValueError, AttributeError):
            pass

        for f in features:
            Building.objects.create(
                geometry=GEOSGeometry(f.geometry.wkt, srid=srid),
                source_dataset=dataset,
                detection_method="CV_DETECTED",
                attributes={"confidence": f.confidence, "method": f.method, "feature_type": f.feature_type},
            )


class MLFeatureExtractor(BaseFeatureExtractor):
    """
    NOT IMPLEMENTED in this MVP - stub only, to demonstrate the abstraction
    that lets a real trained segmentation/detection model (e.g. a U-Net or
    Mask R-CNN fine-tuned on Indian cadastral/building imagery) be plugged in
    later without changing any calling code. Raises explicitly rather than
    silently falling back to CV, so the UI never mislabels CV output as ML.
    """
    model_name = "unconfigured"
    model_version = "n/a"
    method_category = "MACHINE_LEARNING"

    def extract(self, dataset) -> dict:
        raise NotImplementedError(
            "No trained ML model is configured for this deployment. "
            "Use OpenCVFeatureExtractor, or plug in a real trained model here."
        )
