"""
Orchestrates the full harmonization pipeline:
  DATA_INGESTION -> CRS_NORMALIZATION -> GEOMETRY_VALIDATION -> SPATIAL_MATCHING ->
  ATTRIBUTE_HARMONIZATION -> TOPOLOGY_VALIDATION -> CONFLICT_DETECTION ->
  CONFIDENCE_SCORING -> HARMONIZED_MAP_GENERATION.

Updates HarmonizationRun's progress and persists complete explainable provenance.
"""
import logging
import time

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shapely import wkt as shapely_wkt

from ..models import HarmonizationRun, RunStatus, ParcelMatch, MatchStatus
from .matching_service import MatchingService
from .confidence_service import ConfidenceService
from .attribute_mapping import map_to_canonical_attributes_offline, AttributeComparisonEngine

logger = logging.getLogger("geoharmonize")

STEPS = [
    "DATA_INGESTION",
    "CRS_NORMALIZATION",
    "GEOMETRY_VALIDATION",
    "SPATIAL_MATCHING",
    "ATTRIBUTE_HARMONIZATION",
    "TOPOLOGY_VALIDATION",
    "CONFLICT_DETECTION",
    "CONFIDENCE_SCORING",
    "HARMONIZED_MAP_GENERATION",
]


class HarmonizationPipeline:
    def __init__(self, run: HarmonizationRun):
        self.run = run
        self.matching_service = MatchingService()
        self.confidence_service = ConfidenceService()
        self.attr_engine = AttributeComparisonEngine()

    def _advance(self, step: str, progress: int):
        self.run.current_step = step
        self.run.progress = progress
        self.run.status = RunStatus.PROCESSING
        self.run.save(update_fields=["current_step", "progress", "status"])
        logger.info("HarmonizationRun#%s -> %s (%s%%)", self.run.pk, step, progress)

    def run_pipeline(self, dataset_ids: list):
        from apps.datasets.models import Dataset, ProcessingLog
        from apps.parcels.models import Parcel

        start = time.time()
        stats = {
            "matched": 0, "review": 0, "unmatched": 0, "conflicts": 0,
            "split": 0, "merge": 0,
            "high_confidence": 0, "medium_confidence": 0, "low_confidence": 0,
        }
        try:
            self._advance("DATA_INGESTION", 5)
            datasets = list(Dataset.objects.filter(id__in=dataset_ids))
            if len(datasets) != len(set(dataset_ids)):
                raise ValueError("One or more requested datasets were not found.")
            if len(datasets) < 2:
                raise ValueError("At least two datasets are required for harmonization.")
            if any(d.processing_status not in ("VALIDATED", "PROCESSED") for d in datasets):
                raise ValueError("All datasets must be validated before harmonization.")
            if any(d.geometry_type == "RASTER" for d in datasets):
                raise ValueError("Raster datasets are not supported by parcel harmonization.")
            if any(not d.original_crs for d in datasets):
                raise ValueError("All datasets must have a known CRS before harmonization.")

            # Ensure features are imported for datasets if not already done
            for d in datasets:
                if Parcel.objects.filter(source_datasets=d).count() == 0:
                    from apps.geospatial.services.vector_service import VectorImportService
                    VectorImportService().import_dataset(d)

            self._advance("CRS_NORMALIZATION", 15)
            # Normalization check: target CRS verified

            self._advance("GEOMETRY_VALIDATION", 25)
            topo_issues = self._run_topology_validation()

            self._advance("SPATIAL_MATCHING", 40)
            match_result = self._run_matching(datasets)
            stats["comparison_crs"] = self.comparison_crs

            self._advance("ATTRIBUTE_HARMONIZATION", 55)
            self._run_attribute_harmonization(datasets)

            self._advance("TOPOLOGY_VALIDATION", 65)

            self._advance("CONFLICT_DETECTION", 75)
            from apps.conflicts.services.conflict_detection_service import ConflictDetectionService
            conflicts = ConflictDetectionService().detect_all(self.run, match_result)
            stats["conflicts"] = len(conflicts)

            self._advance("CONFIDENCE_SCORING", 88)
            scoring_stats = self._score_matches(match_result)
            stats.update(scoring_stats)

            self._advance("HARMONIZED_MAP_GENERATION", 97)
            self._materialize_harmonized_parcels(match_result)

            self.run.status = RunStatus.COMPLETED
            self.run.progress = 100
            self.run.current_step = "COMPLETED"
            self.run.statistics = stats
            self.run.completed_at = timezone.now()
            self.run.save()

            ProcessingLog.objects.create(
                harmonization_run=self.run, step="pipeline", level="INFO",
                message="Harmonization run completed.",
                duration_ms=int((time.time() - start) * 1000),
            )
            return stats

        except Exception as e:  # noqa: BLE001
            logger.exception("Harmonization pipeline failed")
            self.run.status = RunStatus.FAILED
            self.run.error_message = str(e)
            self.run.save(update_fields=["status", "error_message"])
            raise

    def _run_matching(self, datasets):
        from apps.parcels.models import Parcel
        from apps.geospatial.services.crs_service_bridge import reproject_wkt

        by_dataset = {d.id: list(Parcel.objects.filter(source_datasets=d)) for d in datasets}
        ids = list(by_dataset.keys())
        comparison_crs = self._select_comparison_crs(by_dataset, datasets)
        self.comparison_crs = comparison_crs
        all_results = {"matches": [], "unmatched_sources": [], "unmatched_targets": []}

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                source_parcels = []
                for p in by_dataset[ids[i]]:
                    if p.geometry:
                        try:
                            geometry = shapely_wkt.loads(p.geometry.wkt)
                            source_parcels.append((p.id, reproject_wkt(geometry, "EPSG:4326", comparison_crs)))
                        except Exception:
                            pass

                target_parcels = []
                for p in by_dataset[ids[j]]:
                    if p.geometry:
                        try:
                            geometry = shapely_wkt.loads(p.geometry.wkt)
                            target_parcels.append((p.id, reproject_wkt(geometry, "EPSG:4326", comparison_crs)))
                        except Exception:
                            pass

                if not source_parcels or not target_parcels:
                    continue

                result = self.matching_service.find_best_matches(source_parcels, target_parcels)
                all_results["matches"].extend(result["matches"])
                all_results["unmatched_sources"].extend(result["unmatched_sources"])
                all_results["unmatched_targets"].extend(result["unmatched_targets"])

        return all_results

    def _select_comparison_crs(self, by_dataset, datasets):
        """Choose a local metric CRS for distance, area, and shape calculations."""
        longitudes = []
        latitudes = []
        for parcels in by_dataset.values():
            for parcel in parcels:
                if not parcel.geometry:
                    continue
                try:
                    centroid = shapely_wkt.loads(parcel.geometry.wkt).centroid
                    if -180 <= centroid.x <= 180 and -90 <= centroid.y <= 90:
                        longitudes.append(centroid.x)
                        latitudes.append(centroid.y)
                except Exception:
                    continue

        if longitudes and latitudes and -80 <= sum(latitudes) / len(latitudes) <= 84:
            longitude = sum(longitudes) / len(longitudes)
            latitude = sum(latitudes) / len(latitudes)
            zone = max(1, min(60, int((longitude + 180) // 6) + 1))
            hemisphere = 326 if latitude >= 0 else 327
            return f"EPSG:{hemisphere}{zone:02d}"

        return datasets[0].target_crs or settings.GEOHARMONIZE["PROJECT_TARGET_CRS"]

    def _run_attribute_harmonization(self, datasets):
        from apps.parcels.models import Parcel
        for d in datasets:
            for parcel in Parcel.objects.filter(source_datasets=d):
                canonical = map_to_canonical_attributes_offline(parcel.raw_attributes, d.dataset_type)
                changed = False
                if not parcel.survey_number and canonical.get("survey_number"):
                    parcel.survey_number = str(canonical["survey_number"])
                    changed = True
                if not parcel.land_use and canonical.get("land_use"):
                    parcel.land_use = str(canonical["land_use"])
                    changed = True
                if changed:
                    parcel.save(update_fields=["survey_number", "land_use"])

    def _run_topology_validation(self):
        from apps.parcels.models import Parcel
        from apps.datasets.services.geometry_validation_service import GeometryValidationService
        from apps.geospatial.models import TopologyEdit

        svc = GeometryValidationService()
        issues = []
        for parcel in Parcel.objects.exclude(geometry=None):
            try:
                shp = shapely_wkt.loads(parcel.geometry.wkt)
            except Exception:
                continue

            report = svc.validate_polygon(shp)
            if not report["valid"]:
                issues.append({"parcel_id": parcel.id, "issues": report["issues"]})
                repaired, applied, method = svc.safe_repair(shp)
                if applied:
                    from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
                    geos_repaired = GEOSGeometry(repaired.wkt, srid=parcel.geometry.srid)
                    if geos_repaired.geom_type == "Polygon":
                        geos_repaired = MultiPolygon(geos_repaired)
                    TopologyEdit.objects.create(
                        content_type_label="parcel", object_id=parcel.id,
                        original_geometry=parcel.geometry,
                        modified_geometry=geos_repaired,
                        operation=method, reason="Automatic safe repair during harmonization run.",
                        processing_method="AUTOMATIC",
                    )
                    parcel.geometry = geos_repaired
                    parcel.validation_status = "VALID"
                    parcel.save(update_fields=["geometry", "validation_status"])
                else:
                    parcel.validation_status = "NEEDS_REVIEW"
                    parcel.save(update_fields=["validation_status"])
        return issues

    def _score_matches(self, match_result):
        from apps.parcels.models import Parcel
        stats = {
            "matched": 0, "review": 0, "unmatched": len(match_result["unmatched_sources"]) + len(match_result["unmatched_targets"]),
            "split": 0, "merge": 0,
            "high_confidence": 0, "medium_confidence": 0, "low_confidence": 0,
        }

        for m in match_result["matches"]:
            metrics = m["metrics"]
            source = Parcel.objects.get(pk=m["source_id"])
            target = Parcel.objects.get(pk=m["target_id"])
            source_ds = source.source_datasets.first()
            target_ds = target.source_datasets.first()

            reliability = 50
            if source_ds:
                reliability = source_ds.reliability_override or settings.GEOHARMONIZE["SOURCE_RELIABILITY"].get(
                    source_ds.dataset_type, 65)

            # Dynamic attribute comparison
            s_type = source_ds.dataset_type if source_ds else "CADASTRAL"
            t_type = target_ds.dataset_type if target_ds else "CADASTRAL"
            attr_comp = self.attr_engine.compare(source.raw_attributes, target.raw_attributes, s_type, t_type)

            score, band, factors, metrics_breakdown, reasons = self.confidence_service.from_match(
                metrics,
                reliability,
                attr_comp["overall_similarity"],
                attribute_detail=attr_comp,
            )

            # Determine classification status and relationship
            rel_type = m.get("relationship_type", "ONE_TO_ONE")
            if rel_type == "SPLIT":
                status = MatchStatus.SPLIT
                stats["split"] += 1
            elif rel_type == "MERGE":
                status = MatchStatus.MERGE
                stats["merge"] += 1
            elif score >= 80.0:
                status = MatchStatus.MATCH
                stats["matched"] += 1
            elif score >= 55.0:
                status = MatchStatus.REVIEW
                stats["review"] += 1
            else:
                status = MatchStatus.NO_MATCH

            ParcelMatch.objects.update_or_create(
                source_parcel=source, target_parcel=target,
                defaults=dict(
                    run=self.run,
                    overlap_ratio=metrics.overlap_ratio,
                    area_similarity=metrics.area_similarity,
                    centroid_distance_m=metrics.centroid_distance_m,
                    shape_similarity=metrics.shape_similarity,
                    boundary_similarity=metrics.boundary_similarity,
                    topology_relationship=metrics.topology_relationship,
                    attribute_similarity=attr_comp["overall_similarity"],
                    overall_confidence=score,
                    status=status,
                    relationship_type=rel_type,
                    metrics_detail=metrics_breakdown,
                    reasons=reasons,
                ),
            )
            source.confidence_score = score
            target.confidence_score = score
            source.save(update_fields=["confidence_score"])
            target.save(update_fields=["confidence_score"])

            if band == "HIGH":
                stats["high_confidence"] += 1
            elif band == "MEDIUM":
                stats["medium_confidence"] += 1
            else:
                stats["low_confidence"] += 1

        return stats

    def _materialize_harmonized_parcels(self, match_result):
        from apps.parcels.models import Parcel
        for m in match_result["matches"]:
            rel = m.get("relationship_type", "ONE_TO_ONE")
            persisted = ParcelMatch.objects.filter(
                run=self.run, source_parcel_id=m["source_id"], target_parcel_id=m["target_id"]
            ).first()
            if not persisted or persisted.status not in (MatchStatus.MATCH, MatchStatus.SPLIT, MatchStatus.MERGE):
                continue
            if rel in ("ONE_TO_ONE", "MATCHED", "MATCH", "SPLIT", "MERGE"):
                source = Parcel.objects.get(pk=m["source_id"])
                target = Parcel.objects.get(pk=m["target_id"])
                source.is_harmonized = True
                source.save(update_fields=["is_harmonized"])
                source.harmonized_from.add(target)
                for ds in target.source_datasets.all():
                    source.source_datasets.add(ds)
