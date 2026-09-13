"""
Detects real, measurable conflicts between sources - never fabricated.
Runs against actual harmonization output: ParcelMatch records (for boundary/area/
attribute conflicts), plus direct spatial queries for building/utility crossings
and duplicate/missing-parcel detection.
"""
import logging

from django.conf import settings

from .models_bridge import Parcel, Building, Utility
from ..models import Conflict, ConflictType, Severity, ConflictStatus

logger = logging.getLogger("geoharmonize")

# Thresholds - configurable, not hard-coded magic per-instance.
BOUNDARY_DIFF_LOW_M = 0.3
BOUNDARY_DIFF_MEDIUM_M = 1.0
BOUNDARY_DIFF_HIGH_M = 3.0

AREA_DIFF_LOW_PCT = 5
AREA_DIFF_MEDIUM_PCT = 15
AREA_DIFF_HIGH_PCT = 30


class ConflictDetectionService:

    def detect_all(self, run, match_result) -> list:
        conflicts = []
        conflicts += self._detect_from_matches(run, match_result)
        conflicts += self._detect_missing_parcels(run, match_result)
        conflicts += self._detect_building_parcel_crossings(run)
        conflicts += self._detect_utility_parcel_crossings(run)
        conflicts += self._detect_duplicate_parcels(run)
        return conflicts

    def _severity_from_boundary_diff(self, diff_m: float) -> str:
        if diff_m >= BOUNDARY_DIFF_HIGH_M:
            return Severity.CRITICAL
        if diff_m >= BOUNDARY_DIFF_MEDIUM_M:
            return Severity.HIGH
        if diff_m >= BOUNDARY_DIFF_LOW_M:
            return Severity.MEDIUM
        return Severity.LOW

    def _severity_from_area_diff(self, diff_pct: float) -> str:
        if diff_pct >= AREA_DIFF_HIGH_PCT:
            return Severity.CRITICAL
        if diff_pct >= AREA_DIFF_MEDIUM_PCT:
            return Severity.HIGH
        if diff_pct >= AREA_DIFF_LOW_PCT:
            return Severity.MEDIUM
        return Severity.LOW

    def _detect_from_matches(self, run, match_result) -> list:
        created = []
        for m in match_result["matches"]:
            source = Parcel.objects.get(pk=m["source_id"])
            target = Parcel.objects.get(pk=m["target_id"])
            metrics = m["metrics"]

            # Boundary discrepancy: use a rough symmetric-difference-derived linear
            # measure - approximate boundary offset as sqrt(symmetric_diff_area / avg_perimeter).
            if metrics.overlap_ratio < 1.0 and source.geometry and target.geometry:
                try:
                    from shapely import wkt as shapely_wkt
                    a = shapely_wkt.loads(source.geometry.wkt)
                    b = shapely_wkt.loads(target.geometry.wkt)
                    sym_diff_area = a.symmetric_difference(b).area
                    avg_perimeter = (a.length + b.length) / 2 or 1
                    boundary_diff_m = sym_diff_area / avg_perimeter
                except Exception:
                    boundary_diff_m = 0
                if boundary_diff_m >= BOUNDARY_DIFF_LOW_M:
                    ds_a = source.source_datasets.first()
                    ds_b = target.source_datasets.first()
                    c = Conflict.objects.create(
                        conflict_type=ConflictType.BOUNDARY_DISCREPANCY,
                        severity=self._severity_from_boundary_diff(boundary_diff_m),
                        dataset_a=ds_a, dataset_b=ds_b, parcel_a=source, parcel_b=target,
                        description=f"Boundary offset of ~{boundary_diff_m:.2f} m between "
                                    f"{ds_a.name if ds_a else 'source A'} and {ds_b.name if ds_b else 'source B'}.",
                        measured_difference={"boundary_diff_m": round(boundary_diff_m, 2)},
                        suggested_resolution="Field verification required" if boundary_diff_m >= BOUNDARY_DIFF_MEDIUM_M
                                             else "Accept higher-reliability source",
                        confidence=m["confidence"], run=run,
                        status=ConflictStatus.FIELD_VERIFICATION if boundary_diff_m >= BOUNDARY_DIFF_MEDIUM_M else ConflictStatus.PENDING,
                    )
                    created.append(c)

            # Area mismatch
            if source.area and target.area:
                diff_pct = abs(source.area - target.area) / max(source.area, target.area) * 100
                if diff_pct >= AREA_DIFF_LOW_PCT:
                    c = Conflict.objects.create(
                        conflict_type=ConflictType.AREA_MISMATCH,
                        severity=self._severity_from_area_diff(diff_pct),
                        parcel_a=source, parcel_b=target,
                        dataset_a=source.source_datasets.first(), dataset_b=target.source_datasets.first(),
                        description=f"Area differs by {diff_pct:.1f}% between sources "
                                    f"({source.area:.1f} sqm vs {target.area:.1f} sqm).",
                        measured_difference={"area_diff_pct": round(diff_pct, 2),
                                              "area_a": round(source.area, 2), "area_b": round(target.area, 2)},
                        suggested_resolution="Review against authoritative survey",
                        confidence=m["confidence"], run=run,
                    )
                    created.append(c)

            # Attribute mismatch (land use)
            if source.land_use and target.land_use and source.land_use.strip().lower() != target.land_use.strip().lower():
                c = Conflict.objects.create(
                    conflict_type=ConflictType.ATTRIBUTE_MISMATCH,
                    severity=Severity.MEDIUM,
                    parcel_a=source, parcel_b=target,
                    dataset_a=source.source_datasets.first(), dataset_b=target.source_datasets.first(),
                    description=f"Land use differs: '{source.land_use}' vs '{target.land_use}'.",
                    measured_difference={"land_use_a": source.land_use, "land_use_b": target.land_use},
                    suggested_resolution="Confirm current land use with revenue records",
                    confidence=m["confidence"], run=run,
                )
                created.append(c)
        return created

    def _detect_missing_parcels(self, run, match_result) -> list:
        created = []
        for pid in match_result["unmatched_sources"] + match_result["unmatched_targets"]:
            parcel = Parcel.objects.get(pk=pid)
            ds = parcel.source_datasets.first()
            c = Conflict.objects.create(
                conflict_type=ConflictType.MISSING_IN_SOURCE,
                severity=Severity.MEDIUM,
                parcel_a=parcel, dataset_a=ds,
                description=f"Parcel {parcel.parcel_id or parcel.pk} present in "
                            f"{ds.name if ds else 'a source'} has no corresponding feature in the other source(s).",
                measured_difference={},
                suggested_resolution="Verify whether parcel was newly created, demolished, or missed in the other source.",
                confidence=0, run=run,
            )
            created.append(c)
        return created

    def _detect_building_parcel_crossings(self, run) -> list:
        created = []
        for building in Building.objects.exclude(geometry=None).select_related("parcel"):
            if building.parcel and building.parcel.geometry:
                if not building.parcel.geometry.contains(building.geometry):
                    c = Conflict.objects.create(
                        conflict_type=ConflictType.BUILDING_CROSSES_PARCEL,
                        severity=Severity.HIGH,
                        affected_building=building, parcel_a=building.parcel,
                        dataset_a=building.source_dataset,
                        description=f"Building {building.footprint_id or building.pk} extends beyond its assigned parcel boundary.",
                        measured_difference={}, suggested_resolution="Review building footprint or parcel boundary.",
                        confidence=0, run=run,
                    )
                    created.append(c)
        return created

    def _detect_utility_parcel_crossings(self, run) -> list:
        created = []
        for utility in Utility.objects.exclude(geometry=None):
            crossing_parcels = Parcel.objects.filter(geometry__intersects=utility.geometry).exclude(geometry=None)
            for parcel in crossing_parcels:
                if not parcel.geometry.contains(utility.geometry):
                    c = Conflict.objects.create(
                        conflict_type=ConflictType.UTILITY_CROSSES_PARCEL,
                        severity=Severity.LOW,
                        affected_utility=utility, parcel_a=parcel, dataset_a=utility.source_dataset,
                        description=f"Utility line crosses parcel {parcel.parcel_id or parcel.pk} boundary.",
                        measured_difference={}, suggested_resolution="Confirm utility easement / right-of-way.",
                        confidence=0, run=run,
                    )
                    created.append(c)
        return created

    def _detect_duplicate_parcels(self, run) -> list:
        created = []
        from apps.datasets.services.geometry_validation_service import GeometryValidationService
        from shapely import wkt as shapely_wkt

        svc = GeometryValidationService()
        parcels = list(Parcel.objects.exclude(geometry=None))
        geoms = []
        for p in parcels:
            try:
                geoms.append((p.id, shapely_wkt.loads(p.geometry.wkt)))
            except Exception:
                continue
        dupes = svc.find_duplicates(geoms, tolerance=0.5)
        for d in dupes:
            a = Parcel.objects.get(pk=d["feature_a"])
            b = Parcel.objects.get(pk=d["feature_b"])
            c = Conflict.objects.create(
                conflict_type=ConflictType.DUPLICATE_PARCEL,
                severity=Severity.MEDIUM,
                parcel_a=a, parcel_b=b,
                dataset_a=a.source_datasets.first(), dataset_b=b.source_datasets.first(),
                description=f"Parcels {a.parcel_id or a.pk} and {b.parcel_id or b.pk} have near-identical geometry.",
                measured_difference={}, suggested_resolution="Merge duplicate records.",
                confidence=0, run=run,
            )
            created.append(c)
        return created
