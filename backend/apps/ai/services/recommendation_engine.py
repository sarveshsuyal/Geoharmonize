"""
AI Planning Recommendation Engine for GeoHarmonize.

Evaluates detected bare/vacant land geometries for planning simulations:
  - Agriculture suitability score (0-100)
  - Construction suitability score (0-100)
  - Spatial proximity and exclusion factors
  - Explicit advisory disclaimer (non-binding decision support)
"""
from typing import List, Dict, Any
from shapely.geometry import shape, mapping, Point, Polygon


class PlanningRecommendationEngine:
    DISCLAIMER = (
        "Planning recommendation simulation only. Does not alter legal records "
        "and is not an authoritative government land-use allocation."
    )

    def evaluate_recommendations(self, land_use_features: List[Dict[str, Any]], aoi_polygon: Polygon) -> Dict[str, Any]:
        """
        Evaluates bare land features and assigns agriculture/construction potential.
        """
        # Separate features by category
        bare_features = [f for f in land_use_features if f["properties"].get("land_use") == "BARE_LAND"]
        agri_features = [f for f in land_use_features if f["properties"].get("land_use") == "AGRICULTURE"]
        veg_features = [f for f in land_use_features if f["properties"].get("land_use") == "VEGETATION"]
        water_features = [f for f in land_use_features if f["properties"].get("land_use") == "WATER"]
        road_features = [f for f in land_use_features if f["properties"].get("land_use") == "ROAD"]
        built_features = [f for f in land_use_features if f["properties"].get("land_use") == "BUILT_UP"]

        # Parse shapely geometries
        agri_geoms = [shape(f["geometry"]) for f in agri_features]
        veg_geoms = [shape(f["geometry"]) for f in veg_features]
        water_geoms = [shape(f["geometry"]) for f in water_features]
        road_geoms = [shape(f["geometry"]) for f in road_features]
        built_geoms = [shape(f["geometry"]) for f in built_features]

        # Meters per degree at latitude
        lat_rad = aoi_polygon.centroid.y * (3.14159265 / 180.0)
        m_per_deg = 111320.0

        recommendation_features = []
        agri_candidate_ha = 0.0
        construction_candidate_ha = 0.0

        for bare_feat in bare_features:
            geom = shape(bare_feat["geometry"])
            area_m2 = bare_feat["properties"].get("area_m2", 0.0)
            area_ha = round(area_m2 / 10000.0, 3)

            # Skip tiny slivers
            if area_m2 < 40.0:
                continue

            centroid = geom.centroid

            # Proximities in meters
            dist_water_m = min([centroid.distance(g) * m_per_deg for g in water_geoms], default=9999.0)
            dist_agri_m = min([centroid.distance(g) * m_per_deg for g in agri_geoms], default=9999.0)
            dist_veg_m = min([centroid.distance(g) * m_per_deg for g in veg_geoms], default=9999.0)
            dist_road_m = min([centroid.distance(g) * m_per_deg for g in road_geoms], default=9999.0)
            dist_built_m = min([centroid.distance(g) * m_per_deg for g in built_geoms], default=9999.0)

            # --- 1. Agriculture Suitability Score ---
            agri_score = 30.0
            agri_reasons = []

            if dist_agri_m < 80.0 or dist_veg_m < 60.0:
                agri_score += 25.0
                agri_reasons.append("Adjacent to active agricultural or vegetation zone")
            elif dist_agri_m < 200.0:
                agri_score += 15.0
                agri_reasons.append(f"Near agricultural land ({int(dist_agri_m)}m)")

            if dist_water_m < 250.0:
                agri_score += 25.0
                agri_reasons.append(f"Water source within irrigation distance ({int(dist_water_m)}m)")
            elif dist_water_m < 600.0:
                agri_score += 15.0
                agri_reasons.append(f"Moderate proximity to water body ({int(dist_water_m)}m)")

            if area_m2 >= 500.0:
                agri_score += 15.0
                agri_reasons.append(f"Adequate contiguous farming area ({area_ha} ha)")

            if dist_built_m > 30.0:
                agri_score += 10.0
                agri_reasons.append("Sufficient buffer from dense settlements")
            else:
                agri_score -= 10.0

            agri_score = max(5.0, min(95.0, agri_score))

            # --- 2. Construction Suitability Score ---
            const_score = 30.0
            const_reasons = []

            if dist_road_m < 80.0:
                const_score += 35.0
                const_reasons.append(f"Immediate road network access ({int(dist_road_m)}m)")
            elif dist_road_m < 200.0:
                const_score += 20.0
                const_reasons.append(f"Road network within {int(dist_road_m)}m")

            if dist_built_m < 120.0:
                const_score += 20.0
                const_reasons.append(f"Adjacent to existing built-up infrastructure ({int(dist_built_m)}m)")
            elif dist_built_m < 350.0:
                const_score += 10.0
                const_reasons.append("Near existing settlement corridor")

            if dist_water_m > 50.0:
                const_score += 15.0
                const_reasons.append("Safe setback distance from water hazard")
            else:
                const_score -= 25.0
                const_reasons.append("Caution: Within flood setback zone (<50m to water)")

            if area_m2 >= 300.0:
                const_score += 15.0
                const_reasons.append(f"Adequate contiguous construction footprint ({area_ha} ha)")

            const_score = max(5.0, min(95.0, const_score))

            # Determine dominant recommendation
            if agri_score >= 60.0 and agri_score > const_score:
                rec_type = "AGRICULTURE"
                label = "Agriculture Candidate"
                score = round(agri_score, 1)
                reasons = agri_reasons
                color = "#10b981"
                stroke_color = "#059669"
                agri_candidate_ha += area_ha
            elif const_score >= 55.0 and const_score >= agri_score:
                rec_type = "CONSTRUCTION"
                label = "Construction Candidate"
                score = round(const_score, 1)
                reasons = const_reasons
                color = "#f97316"
                stroke_color = "#ea580c"
                construction_candidate_ha += area_ha
            elif max(agri_score, const_score) >= 45.0:
                if agri_score >= const_score:
                    rec_type = "AGRICULTURE"
                    label = "Agriculture Candidate"
                    score = round(agri_score, 1)
                    reasons = agri_reasons
                    color = "#10b981"
                    stroke_color = "#059669"
                    agri_candidate_ha += area_ha
                else:
                    rec_type = "CONSTRUCTION"
                    label = "Construction Candidate"
                    score = round(const_score, 1)
                    reasons = const_reasons
                    color = "#f97316"
                    stroke_color = "#ea580c"
                    construction_candidate_ha += area_ha
            else:
                rec_type = "NOT_RECOMMENDED"
                label = "Insufficient Confidence"
                score = round(max(agri_score, const_score), 1)
                reasons = ["Low suitability across agricultural and development metrics", "Requires field inspection"]
                color = "#94a3b8"
                stroke_color = "#64748b"

            conf = round(min(90.0, max(55.0, 50.0 + score * 0.4)), 1)

            rec_feature = {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "recommendation_type": rec_type,
                    "label": label,
                    "suitability_score": score,
                    "agriculture_score": round(agri_score, 1),
                    "construction_score": round(const_score, 1),
                    "confidence": conf,
                    "area_m2": round(area_m2, 1),
                    "area_ha": area_ha,
                    "reasons": reasons,
                    "color": color,
                    "stroke_color": stroke_color,
                    "disclaimer": self.DISCLAIMER,
                },
            }
            recommendation_features.append(rec_feature)

        return {
            "feature_collection": {
                "type": "FeatureCollection",
                "features": recommendation_features,
            },
            "summary": {
                "total_candidates": len(recommendation_features),
                "agriculture_candidate_ha": round(agri_candidate_ha, 3),
                "construction_candidate_ha": round(construction_candidate_ha, 3),
                "disclaimer": self.DISCLAIMER,
            },
        }
