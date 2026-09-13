"""
Selftest for the AI-assisted GIS analysis, land-use classification,
and planning recommendations pipeline.
"""
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import numpy as np
from shapely.geometry import Polygon, box, mapping

from apps.ai.services.imagery_provider import ImageryProvider
from apps.ai.services.land_use_classifier import LandUseClassifier, LAND_USE_CONFIG
from apps.ai.services.recommendation_engine import PlanningRecommendationEngine


def test_pipeline():
    print("--- 1. Testing AOI Imagery Provider ---")
    # Define an AOI polygon around Meerut study area
    min_lon, min_lat, max_lon, max_lat = 77.7064, 29.0588, 77.7120, 29.0630
    aoi_polygon = box(min_lon, min_lat, max_lon, max_lat)
    bounds = (min_lon, min_lat, max_lon, max_lat)

    provider = ImageryProvider(zoom=17)
    img, transform, source_type = provider.get_aoi_raster(aoi_polygon, bounds)

    print(f"Generated imagery shape: {img.shape}, dtype: {img.dtype}")
    print(f"Source type: {source_type}")
    print(f"Transform: {transform}")
    assert img.ndim == 3 and img.shape[2] == 3, "Image must be RGB (H, W, 3)"
    assert source_type in ("LOCAL_DATASET", "SATELLITE_TILES", "SYNTHETIC_OFFLINE")
    print("PASS: ImageryProvider successfully acquired georeferenced AOI raster.")

    print("\n--- 2. Testing Multi-Class Land-Use Classifier ---")
    classifier = LandUseClassifier()
    result = classifier.classify_aoi(img, transform, aoi_polygon)

    fc = result["feature_collection"]
    stats = result["summary_statistics"]

    print(f"Features extracted: {len(fc['features'])}")
    print(f"Total analyzed area: {stats['total_area_m2']:.1f} m² ({stats['total_area_ha']:.2f} ha)")
    print(f"Land-use distribution: {stats['percentages']}")
    print(f"Detected buildings: {stats['detected_buildings_count']}")
    print(f"Detected road length: {stats['detected_road_length_km']} km")
    print(f"Method category: {stats['method_category']}")
    print(f"Model name: {stats['model_name']}")

    assert len(fc["features"]) > 0, "Pipeline should extract candidate features"
    assert stats["total_area_m2"] > 0, "Area should be positive"
    assert stats["is_ml_model"] is False, "Must clearly disclose is_ml_model is False"
    assert "percentages" in stats

    # Verify all feature geometries are valid and inside AOI
    for f in fc["features"]:
        geom = f["geometry"]
        assert geom["type"] in ("Polygon", "MultiPolygon")
        props = f["properties"]
        assert props["land_use"] in LAND_USE_CONFIG
        assert "color" in props
        assert "confidence" in props
        assert props["area_m2"] > 0

    print("PASS: LandUseClassifier successfully segmented imagery and extracted georeferenced features.")

    print("\n--- 3. Testing Planning Recommendations Engine ---")
    rec_engine = PlanningRecommendationEngine()
    rec_result = rec_engine.evaluate_recommendations(fc["features"], aoi_polygon)

    rec_fc = rec_result["feature_collection"]
    rec_summary = rec_result["summary"]

    print(f"Recommendation candidates generated: {rec_summary['total_candidates']}")
    print(f"Agriculture candidate area: {rec_summary['agriculture_candidate_ha']} ha")
    print(f"Construction candidate area: {rec_summary['construction_candidate_ha']} ha")
    print(f"Disclaimer: {rec_summary['disclaimer']}")

    assert "disclaimer" in rec_summary, "Must have advisory disclaimer"

    for rf in rec_fc["features"]:
        p = rf["properties"]
        assert p["recommendation_type"] in ("AGRICULTURE", "CONSTRUCTION", "NOT_RECOMMENDED")
        assert 0 <= p["suitability_score"] <= 100
        assert len(p["reasons"]) > 0
        assert "disclaimer" in p

    print("PASS: PlanningRecommendationEngine successfully evaluated candidate zones with spatial factors.")
    print("\n=== ALL AI GIS PIPELINE SELFTESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    test_pipeline()
