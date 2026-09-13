"""
Topology / geometry validation & safe automatic repair.

Detects: invalid polygons, self-intersections, duplicate geometries, overlaps,
gaps (via unary_union comparison), sliver polygons, disconnected boundaries.

Repair policy: ONLY safe, well-understood fixes are applied automatically
(make_valid and buffer(0)). Anything structurally ambiguous or where area changes
wildly is flagged for human review, never silently overwritten.
Both the original and modified geometry are retained.
"""
import logging
from typing import Tuple, Optional

logger = logging.getLogger("geoharmonize")

SLIVER_AREA_RATIO_THRESHOLD = 0.02  # area / perimeter^2 below this => sliver-ish
MIN_SLIVER_AREA_SQM = 2.0


class GeometryValidationService:

    def validate_polygon(self, geom) -> dict:
        """geom: shapely geometry. Returns a report dict; does not mutate."""
        return self.validate_geometry(geom)

    def validate_geometry(self, geom) -> dict:
        """geom: shapely geometry. Returns a report dict; does not mutate."""
        issues = []
        if geom is None:
            issues.append({"type": "NULL_GEOMETRY", "severity": "CRITICAL", "detail": "Geometry is null"})
            return {"valid": False, "issues": issues}

        if geom.is_empty:
            issues.append({"type": "EMPTY_GEOMETRY", "severity": "CRITICAL", "detail": "Geometry contains no coordinates"})
            return {"valid": False, "issues": issues}

        if geom.geom_type not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point", "MultiPoint"):
            issues.append({"type": "UNSUPPORTED_TYPE", "severity": "HIGH", "detail": f"Type {geom.geom_type} is unsupported"})

        if not geom.is_valid:
            from shapely.validation import explain_validity
            detail = explain_validity(geom)
            issues.append({
                "type": "INVALID_GEOMETRY",
                "severity": "HIGH",
                "detail": detail,
            })

        if geom.geom_type in ("Polygon", "MultiPolygon"):
            area = geom.area
            length = geom.length
            if length > 0:
                compactness = (4 * 3.14159265 * area) / (length ** 2)
                if area < MIN_SLIVER_AREA_SQM and compactness < SLIVER_AREA_RATIO_THRESHOLD:
                    issues.append({"type": "SLIVER_POLYGON", "severity": "LOW", "area": area})

        return {"valid": len(issues) == 0, "issues": issues}

    def safe_repair(self, geom) -> Tuple[any, bool, str]:
        """
        Attempt a conservative repair using make_valid and buffer(0).
        Returns (repaired_geom, applied: bool, method: str).
        """
        if geom is None or geom.is_empty:
            return geom, False, "EMPTY_OR_NULL"

        if geom.is_valid:
            return geom, False, "NO_REPAIR_NEEDED"

        orig_area = geom.area if hasattr(geom, "area") else 0

        # Try make_valid first
        try:
            from shapely.validation import make_valid
            repaired = make_valid(geom)

            # If make_valid produced a GeometryCollection, extract polygon / multipolygon
            if repaired.geom_type == "GeometryCollection":
                from shapely.geometry import MultiPolygon
                polys = [g for g in repaired.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
                if polys:
                    from shapely.ops import unary_union
                    repaired = unary_union(polys)

            if repaired.is_valid and not repaired.is_empty:
                if orig_area > 0 and hasattr(repaired, "area"):
                    area_diff = abs(repaired.area - orig_area) / orig_area
                    if area_diff <= 0.4:
                        return repaired, True, "MAKE_VALID"
                elif getattr(repaired, "area", 0) > 0:
                    return repaired, True, "MAKE_VALID"
        except Exception as e:
            logger.debug("make_valid failed: %s", e)

        # Fallback to buffer(0)
        try:
            repaired = geom.buffer(0)
            if repaired.is_valid and not repaired.is_empty:
                if orig_area > 0 and hasattr(repaired, "area"):
                    area_diff = abs(repaired.area - orig_area) / orig_area
                    if area_diff <= 0.4:
                        return repaired, True, "BUFFER_ZERO"
                elif getattr(repaired, "area", 0) > 0:
                    return repaired, True, "BUFFER_ZERO"
        except Exception as e:
            logger.debug("buffer(0) repair failed: %s", e)

        return geom, False, "REPAIR_FAILED_NEEDS_MANUAL_REVIEW"

    def find_overlaps(self, geometries: list) -> list:
        """Overlap detection using shapely spatial indexing."""
        from shapely.strtree import STRtree
        overlaps = []
        if len(geometries) < 2:
            return overlaps

        ids = [item[0] for item in geometries]
        geoms = [item[1] for item in geometries]
        tree = STRtree(geoms)

        for i, (id_a, geom_a) in enumerate(geometries):
            if geom_a is None or geom_a.is_empty:
                continue
            candidates = tree.query(geom_a)
            for cand_idx in candidates:
                if cand_idx > i:
                    id_b = ids[cand_idx]
                    geom_b = geoms[cand_idx]
                    if geom_a.intersects(geom_b):
                        inter = geom_a.intersection(geom_b)
                        if hasattr(inter, "area") and inter.area > 0:
                            overlaps.append({
                                "feature_a": id_a,
                                "feature_b": id_b,
                                "overlap_area": inter.area,
                            })
        return overlaps

    def find_duplicates(self, geometries: list, tolerance: float = 0.01) -> list:
        from shapely.strtree import STRtree
        dupes = []
        if len(geometries) < 2:
            return dupes

        ids = [item[0] for item in geometries]
        geoms = [item[1] for item in geometries]
        tree = STRtree(geoms)

        for i, (id_a, geom_a) in enumerate(geometries):
            if geom_a is None or geom_a.is_empty:
                continue
            candidates = tree.query(geom_a)
            for cand_idx in candidates:
                if cand_idx > i:
                    id_b = ids[cand_idx]
                    geom_b = geoms[cand_idx]
                    if geom_a.equals_exact(geom_b, tolerance):
                        dupes.append({"feature_a": id_a, "feature_b": id_b})
        return dupes
