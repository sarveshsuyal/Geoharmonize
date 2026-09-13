"""
Land-Use and Feature Extraction Classifier for GeoHarmonize.

Performs deterministic multi-class spectral and morphological segmentation
over orthorectified imagery:
  1. Built-up / Occupied (RED #ef4444)
  2. Bare / Vacant Land (GREEN #22c55e)
  3. Agriculture / Cropland (YELLOW #eab308)
  4. Vegetation / Green Areas (DARK GREEN #15803d)
  5. Water Bodies (BLUE #3b82f6)
  6. Roads / Infrastructure (ORANGE #f97316)
  7. Other / Unknown (GRAY #64748b)

All geometries are georeferenced and clipped strictly to the AOI polygon.
Clearly declared as COMPUTER_VISION_HEURISTIC, not a trained ML model.
"""
import time
from typing import Dict, List, Any, Tuple
import cv2
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.validation import make_valid

from apps.geospatial.services.raster_service import RasterService


LAND_USE_CONFIG = {
    "BUILT_UP": {
        "label": "Built-up / Occupied",
        "color": "#ef4444",
        "stroke": "#b91c1c",
    },
    "BARE_LAND": {
        "label": "Bare / Vacant Land",
        "color": "#22c55e",
        "stroke": "#15803d",
    },
    "AGRICULTURE": {
        "label": "Agriculture / Cropland",
        "color": "#eab308",
        "stroke": "#a16207",
    },
    "VEGETATION": {
        "label": "Vegetation / Green Area",
        "color": "#15803d",
        "stroke": "#14532d",
    },
    "WATER": {
        "label": "Water Body",
        "color": "#3b82f6",
        "stroke": "#1d4ed8",
    },
    "ROAD": {
        "label": "Roads / Infrastructure",
        "color": "#f97316",
        "stroke": "#c2410c",
    },
    "UNKNOWN": {
        "label": "Other / Unknown",
        "color": "#64748b",
        "stroke": "#334155",
    },
}


class LandUseClassifier:
    model_name = "GeoHarmonize Classical CV & Spectral Classifier"
    model_version = "1.0-prototype"
    method_category = "COMPUTER_VISION_HEURISTIC"
    is_ml_model = False

    def __init__(self):
        self.raster_service = RasterService()

    def classify_aoi(self, img_rgb: np.ndarray, transform, aoi_polygon: Polygon) -> Dict[str, Any]:
        """
        Executes multi-class classification and vector feature extraction.
        """
        start_time = time.time()
        h, w = img_rgb.shape[:2]

        # 1. Color space transformations & indices
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        r = img_rgb[:, :, 0].astype(np.float32)
        g = img_rgb[:, :, 1].astype(np.float32)
        b = img_rgb[:, :, 2].astype(np.float32)

        # Excess Green Index (2G - R - B) for vegetation detection
        exg = 2.0 * g - r - b

        # 2. Mask generation per class
        # Water: high blue-to-red ratio, low brightness, or water HSV range
        water_mask = ((b > r + 15) & (b > g) & (gray < 160)) | ((hsv[:, :, 0] >= 90) & (hsv[:, :, 0] <= 135) & (hsv[:, :, 1] > 40) & (hsv[:, :, 2] < 180))
        water_mask = cv2.morphologyEx(water_mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        # Vegetation: strong excess green, dark-to-moderate value
        veg_mask = (exg > 20) & (g > r) & (g > b) & ~water_mask.astype(bool)
        dense_veg_mask = veg_mask & (hsv[:, :, 2] < 140)

        # Agriculture: moderate vegetation index or yellow-green tones, regular field texture
        agri_mask = (veg_mask & ~dense_veg_mask) | ((hsv[:, :, 0] >= 22) & (hsv[:, :, 0] <= 45) & (hsv[:, :, 1] > 35) & ~water_mask.astype(bool))

        # Built-up: high edge gradient, high local contrast, distinct rectangularity
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 45, 130)
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
        kernel_large = np.ones((7, 7), np.uint8)
        edge_density = cv2.boxFilter(closed_edges.astype(np.float32) / 255.0, -1, (15, 15))
        built_up_mask = (edge_density > 0.18) & (gray > 120) & ~veg_mask & ~water_mask.astype(bool)
        built_up_mask = cv2.morphologyEx(built_up_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel_large)

        # Roads: high linearity, elongated neutral grey/dark paths
        road_mask = (np.abs(r - g) < 12) & (np.abs(g - b) < 12) & (gray > 90) & (gray < 175) & ~built_up_mask.astype(bool) & ~veg_mask
        road_mask = cv2.morphologyEx(road_mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        # Bare / Vacant: residual non-vegetated soil tones, unbuilt, non-water
        bare_mask = (r > g) & (g > b) & (gray > 95) & ~built_up_mask.astype(bool) & ~veg_mask & ~water_mask.astype(bool) & ~road_mask.astype(bool)

        # 3. Vectorize masks to map polygons
        masks = [
            ("BUILT_UP", built_up_mask, 120),
            ("WATER", water_mask, 80),
            ("VEGETATION", dense_veg_mask, 150),
            ("AGRICULTURE", agri_mask, 250),
            ("ROAD", road_mask, 100),
            ("BARE_LAND", bare_mask, 200),
        ]

        features = []
        class_areas = {k: 0.0 for k in LAND_USE_CONFIG.keys()}
        detected_buildings_count = 0
        detected_road_length_m = 0.0

        # Approx degree-to-meters conversion at latitude
        lat_rad = np.radians(aoi_polygon.centroid.y)
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * np.cos(lat_rad)

        for feature_type, mask, min_area_px in masks:
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area_px = cv2.contourArea(cnt)
                if area_px < min_area_px:
                    continue

                epsilon = 0.015 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                pixel_coords = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
                if len(pixel_coords) < 3:
                    continue

                poly = self.raster_service.pixel_polygon_to_map_polygon(transform, pixel_coords)
                if poly is None or not poly.is_valid or poly.is_empty:
                    continue

                # Strictly clip to AOI polygon
                try:
                    clipped = poly.intersection(aoi_polygon)
                    if clipped.is_empty:
                        continue
                    clipped = make_valid(clipped)
                except Exception:
                    continue

                # Measure area in m²
                polys_to_add = [clipped] if isinstance(clipped, Polygon) else [p for p in getattr(clipped, "geoms", []) if isinstance(p, Polygon)]
                for p in polys_to_add:
                    if p.is_empty or not p.is_valid:
                        continue
                    deg_area = float(p.area)
                    area_m2 = float(deg_area * m_per_deg_lat * m_per_deg_lon)
                    if area_m2 < 10:
                        continue

                    # Compute confidence proxy
                    hull = cv2.convexHull(cnt)
                    hull_area = float(cv2.contourArea(hull) or 1)
                    solidity = min(1.0, float(area_px) / hull_area)
                    base_conf = 72.0 + solidity * 20.0
                    confidence = float(round(min(94.0, max(65.0, base_conf)), 1))

                    if feature_type == "BUILT_UP":
                        detected_buildings_count += 1
                    elif feature_type == "ROAD":
                        detected_road_length_m += float(np.sqrt(area_m2) * 2.5)

                    class_areas[feature_type] += area_m2

                    cfg = LAND_USE_CONFIG[feature_type]
                    feat_dict = {
                        "type": "Feature",
                        "geometry": mapping(p),
                        "properties": {
                            "feature_type": feature_type,
                            "land_use": feature_type,
                            "label": cfg["label"],
                            "color": cfg["color"],
                            "stroke_color": cfg["stroke"],
                            "area_m2": round(area_m2, 1),
                            "area_ha": round(area_m2 / 10000.0, 3),
                            "confidence": confidence,
                            "method": self.method_category,
                        },
                    }
                    features.append(feat_dict)

        # 4. Total area and statistics
        total_aoi_m2 = float(aoi_polygon.area * m_per_deg_lat * m_per_deg_lon)
        total_classified_m2 = float(sum(class_areas.values()))
        if total_classified_m2 < total_aoi_m2:
            class_areas["UNKNOWN"] = total_aoi_m2 - total_classified_m2

        percentages = {}
        for k, v in class_areas.items():
            pct = float(round((float(v) / max(1.0, total_aoi_m2)) * 100.0, 1))
            percentages[k] = pct

        elapsed_ms = int((time.time() - start_time) * 1000)

        feature_collection = {
            "type": "FeatureCollection",
            "features": features,
        }

        return {
            "feature_collection": feature_collection,
            "summary_statistics": {
                "total_area_m2": round(total_aoi_m2, 1),
                "total_area_ha": round(total_aoi_m2 / 10000.0, 2),
                "percentages": percentages,
                "class_areas_m2": {k: round(float(v), 1) for k, v in class_areas.items()},
                "class_areas_ha": {k: round(float(v) / 10000.0, 3) for k, v in class_areas.items()},
                "detected_buildings_count": int(detected_buildings_count),
                "detected_road_length_km": round(float(detected_road_length_m) / 1000.0, 2),
                "feature_count": len(features),
                "processing_time_ms": elapsed_ms,
                "method_category": self.method_category,
                "model_name": self.model_name,
                "model_version": self.model_version,
                "is_ml_model": self.is_ml_model,
                "note": "Deterministic computer-vision spectral and morphological segmentation. Not a deep-learning weights model; provides rapid GIS estimation.",
            },
        }
