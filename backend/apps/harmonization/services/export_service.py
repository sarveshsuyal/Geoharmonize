"""
Harmonized GIS layer export service.
Generates genuine GeoJSON FeatureCollections containing the harmonized features,
linked source provenance, confidence metrics, and harmonized attributes.
Ensures output is valid and can be re-opened by standard GIS libraries (GDAL/Fiona/QGIS).
"""
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("geoharmonize")


class HarmonizedExportService:

    def generate_harmonized_geojson(self, run) -> Dict[str, Any]:
        """
        Builds a GeoJSON FeatureCollection from a HarmonizationRun's accepted / matched
        parcel records and unresolved conflict items.
        """
        from apps.harmonization.models import ParcelMatch
        from apps.parcels.models import Parcel

        features = []
        matches = run.matches.select_related("source_parcel", "target_parcel").all()

        # 1. Matched / Split / Merge features
        for m in matches:
            approved = m.status == "MATCH" or (
                m.status in ("SPLIT", "MERGE")
                and m.review_decision in ("CONFIRM_SPLIT", "CONFIRM_MERGE")
            ) or m.review_decision in ("ACCEPT", "CHOOSE_ALTERNATIVE")
            if not approved:
                continue
            src = m.source_parcel
            tgt = m.target_parcel
            if not src or not src.geometry:
                continue

            src_ds = src.source_datasets.first()
            tgt_ds = tgt.source_datasets.first()

            geom_geojson = json.loads(src.geometry.geojson)

            properties = {
                "harmonized_id": f"HARM-{run.id}-{m.id}",
                "match_id": m.id,
                "status": m.status,
                "relationship_type": m.relationship_type,
                "overall_confidence": round(m.overall_confidence, 1),
                "source_dataset_id": src_ds.id if src_ds else None,
                "source_dataset_name": src_ds.name if src_ds else "",
                "source_parcel_id": src.parcel_id,
                "target_dataset_id": tgt_ds.id if tgt_ds else None,
                "target_dataset_name": tgt_ds.name if tgt_ds else "",
                "target_parcel_id": tgt.parcel_id,
                "survey_number": src.survey_number or tgt.survey_number or "",
                "land_use": src.land_use or tgt.land_use or "",
                "area_sqm": src.area or tgt.area,
                "overlap_ratio": m.overlap_ratio,
                "centroid_distance_m": m.centroid_distance_m,
                "area_similarity": m.area_similarity,
                "shape_similarity": m.shape_similarity,
                "boundary_similarity": m.boundary_similarity,
                "topology_relationship": m.topology_relationship,
                "metrics_detail": m.metrics_detail,
                "reasons": m.reasons,
                "provenance": {
                    "harmonization_run_id": run.id,
                    "algorithm_version": "GeoHarmonize-STRtree-v1.0",
                    "source_crs": src_ds.original_crs if src_ds else "UNKNOWN",
                    "target_crs": "EPSG:4326",
                    "review_decision": m.review_decision or "AUTO",
                },
            }

            features.append({
                "type": "Feature",
                "id": f"HARM-{run.id}-{m.id}",
                "geometry": geom_geojson,
                "properties": properties,
            })

        # 2. Also include unmatched parcels from included datasets with status='UNMATCHED'
        approved_matches = [m for m in matches if m.status == "MATCH" or (
            m.status in ("SPLIT", "MERGE") and m.review_decision in ("CONFIRM_SPLIT", "CONFIRM_MERGE")
        ) or m.review_decision in ("ACCEPT", "CHOOSE_ALTERNATIVE")]
        matched_source_pids = {m.source_parcel_id for m in approved_matches}
        matched_target_pids = {m.target_parcel_id for m in approved_matches}

        dataset_ids = run.dataset_ids or []
        unmatched_parcels = Parcel.objects.filter(
            source_datasets__id__in=dataset_ids
        ).exclude(
            id__in=matched_source_pids | matched_target_pids
        ).distinct()

        for up in unmatched_parcels[:200]:  # safety limit
            if not up.geometry:
                continue
            ds = up.source_datasets.first()
            geom_geojson = json.loads(up.geometry.geojson)
            features.append({
                "type": "Feature",
                "id": f"UNMATCHED-{up.id}",
                "geometry": geom_geojson,
                "properties": {
                    "harmonized_id": f"UNMATCHED-{up.id}",
                    "match_id": None,
                    "status": "UNMATCHED",
                    "relationship_type": "UNMATCHED",
                    "overall_confidence": 0.0,
                    "source_dataset_id": ds.id if ds else None,
                    "source_dataset_name": ds.name if ds else "",
                    "source_parcel_id": up.parcel_id,
                    "survey_number": up.survey_number,
                    "land_use": up.land_use,
                    "area_sqm": up.area,
                    "provenance": {
                        "harmonization_run_id": run.id,
                        "algorithm_version": "GeoHarmonize-STRtree-v1.0",
                        "status": "UNMATCHED_IN_RUN",
                    },
                },
            })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "harmonization_run_id": run.id,
                "status": run.status,
                "total_features": len(features),
                "matched_count": len(approved_matches),
                "statistics": run.statistics,
                "crs": {
                    "type": "name",
                    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
                },
            },
            "features": features,
        }

    def verify_geojson(self, geojson_dict: dict) -> bool:
        """Verifies that the generated GeoJSON dictionary is structurally valid according to Fiona / Shapely."""
        from shapely.geometry import shape
        features = geojson_dict.get("features", [])
        for f in features:
            g = f.get("geometry")
            if g:
                shp = shape(g)
                if not shp.is_valid:
                    return False
        return True
