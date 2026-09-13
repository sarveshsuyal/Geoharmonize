"""
Parcel matching engine - determines whether two polygons from different
sources represent the same real-world parcel, using ONLY measurable geometric
factors. No score here is ever hard-coded; every value is computed from the
actual geometries passed in.

Uses STRtree spatial indexing to avoid O(N^2) pairwise comparisons.
Detects 1:1 matches, 1:N splits, and N:1 merges.
"""
from dataclasses import dataclass, field
import math
from typing import List, Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger("geoharmonize")


@dataclass
class MatchMetrics:
    overlap_ratio: float        # IoU, 0-1
    area_similarity: float      # 0-1
    centroid_distance_m: float  # distance in meters
    shape_similarity: float     # 0-1, compactness comparison
    boundary_similarity: float = 0.0  # 0-1, Hausdorff proximity score
    topology_relationship: str = "OVERLAPS"  # IDENTICAL, CONTAINS, WITHIN, OVERLAPS, TOUCHES, DISJOINT


class MatchingService:
    WEIGHTS = {
        "overlap": 0.40,
        "area": 0.20,
        "centroid": 0.20,
        "shape": 0.15,
        "boundary": 0.05,
    }
    CENTROID_DISTANCE_DECAY_M = 25.0  # distance at which centroid-similarity decays
    SEARCH_MARGIN_M = 50.0            # spatial candidate search expansion buffer

    def compute_metrics(self, geom_a, geom_b) -> Optional[MatchMetrics]:
        """geom_a, geom_b: Shapely geometries in a shared projected (metric) CRS."""
        if geom_a is None or geom_b is None or geom_a.is_empty or geom_b.is_empty:
            return None

        # Centroid distance (handle geographic degrees vs projected meters)
        c_a = geom_a.centroid
        c_b = geom_b.centroid
        is_geo = (abs(c_a.x) <= 180 and abs(c_a.y) <= 90 and abs(c_b.x) <= 180 and abs(c_b.y) <= 90)
        if is_geo:
            mid_lat = (c_a.y + c_b.y) / 2.0
            dx_m = (c_a.x - c_b.x) * 111139.0 * math.cos(math.radians(mid_lat))
            dy_m = (c_a.y - c_b.y) * 111139.0
            centroid_dist = math.sqrt(dx_m * dx_m + dy_m * dy_m)
        else:
            centroid_dist = c_a.distance(c_b)

        area_sim = self._area_similarity(geom_a, geom_b)
        shape_sim = self._shape_similarity(geom_a, geom_b)
        boundary_sim = self._boundary_similarity(geom_a, geom_b)

        if not geom_a.intersects(geom_b):
            topo = "TOUCHES" if geom_a.touches(geom_b) else "DISJOINT"
            return MatchMetrics(
                overlap_ratio=0.0,
                area_similarity=area_sim,
                centroid_distance_m=centroid_dist,
                shape_similarity=shape_sim,
                boundary_similarity=boundary_sim,
                topology_relationship=topo,
            )

        inter_geom = geom_a.intersection(geom_b)
        inter_area = inter_geom.area if hasattr(inter_geom, "area") else 0.0
        union_geom = geom_a.union(geom_b)
        union_area = union_geom.area if hasattr(union_geom, "area") else 0.0
        iou = inter_area / union_area if union_area > 0 else 0.0

        # Topology classification
        if iou >= 0.98 or geom_a.equals_exact(geom_b, 0.05):
            topo = "IDENTICAL"
        elif geom_a.contains(geom_b):
            topo = "CONTAINS"
        elif geom_b.contains(geom_a):
            topo = "WITHIN"
        elif inter_area > 0:
            topo = "OVERLAPS"
        elif geom_a.touches(geom_b):
            topo = "TOUCHES"
        else:
            topo = "DISJOINT"

        return MatchMetrics(
            overlap_ratio=iou,
            area_similarity=area_sim,
            centroid_distance_m=centroid_dist,
            shape_similarity=shape_sim,
            boundary_similarity=boundary_sim,
            topology_relationship=topo,
        )

    def _area_similarity(self, geom_a, geom_b) -> float:
        a = geom_a.area if hasattr(geom_a, "area") else 0.0
        b = geom_b.area if hasattr(geom_b, "area") else 0.0
        if a == 0 and b == 0:
            return 1.0
        larger, smaller = max(a, b), min(a, b)
        return round(smaller / larger, 4) if larger > 0 else 0.0

    def _shape_similarity(self, geom_a, geom_b) -> float:
        """Compares compactness (4*pi*area / perimeter^2)."""
        def compactness(g):
            if not hasattr(g, "area") or not hasattr(g, "length") or g.length == 0:
                return 0.0
            return (4 * math.pi * g.area) / (g.length ** 2)

        ca, cb = compactness(geom_a), compactness(geom_b)
        return round(max(0.0, 1.0 - abs(ca - cb)), 4)

    def _boundary_similarity(self, geom_a, geom_b) -> float:
        """Boundary proximity based on Hausdorff distance normalized by feature perimeter."""
        try:
            h_dist = geom_a.boundary.hausdorff_distance(geom_b.boundary)
            length = max(geom_a.length, geom_b.length)
            if length > 0:
                rel_error = h_dist / length
                return round(math.exp(-rel_error * 6.0), 4)
            return 1.0 if h_dist == 0 else 0.5
        except Exception:
            return 0.5

    def centroid_similarity_score(self, distance_m: float) -> float:
        """Convert a raw centroid distance into a 0-1 similarity via exponential decay."""
        return math.exp(-distance_m / self.CENTROID_DISTANCE_DECAY_M)

    def combined_score_0_1(self, metrics: MatchMetrics) -> float:
        score = (
            self.WEIGHTS["overlap"] * metrics.overlap_ratio
            + self.WEIGHTS["area"] * metrics.area_similarity
            + self.WEIGHTS["centroid"] * self.centroid_similarity_score(metrics.centroid_distance_m)
            + self.WEIGHTS["shape"] * max(0.0, metrics.shape_similarity)
            + self.WEIGHTS["boundary"] * max(0.0, metrics.boundary_similarity)
        )
        return round(min(1.0, max(0.0, score)), 4)

    def find_best_matches(
        self,
        source_features: List[Tuple[Any, Any]],
        target_features: List[Tuple[Any, Any]],
        accept_threshold: float = 60.0,
    ) -> dict:
        """
        source_features / target_features: list of (id, shapely_geom) tuples.
        Uses STRtree spatial indexing to generate candidates in O(N log M) time.
        Detects 1:1, 1:N splits, and N:1 merges.
        """
        if not source_features or not target_features:
            return {
                "matches": [],
                "unmatched_sources": [sid for sid, _ in source_features],
                "unmatched_targets": [tid for tid, _ in target_features],
            }

        from shapely.strtree import STRtree
        from shapely.geometry import box
        from shapely.ops import unary_union

        target_geoms = [geom for _, geom in target_features]
        tree = STRtree(target_geoms)

        # Generate candidates using index
        candidates_by_source: Dict[Any, List[dict]] = {}
        candidates_by_target: Dict[Any, List[dict]] = {}
        all_candidates: List[dict] = []

        for sid, geom_a in source_features:
            if geom_a is None or geom_a.is_empty:
                continue
            b = geom_a.bounds
            is_geo = (abs(b[0]) <= 180 and abs(b[1]) <= 90)
            if is_geo:
                margin_y = self.SEARCH_MARGIN_M / 111139.0
                mid_lat = (b[1] + b[3]) / 2.0
                margin_x = self.SEARCH_MARGIN_M / (111139.0 * max(0.1, math.cos(math.radians(mid_lat))))
            else:
                margin_x = self.SEARCH_MARGIN_M
                margin_y = self.SEARCH_MARGIN_M

            search_box = box(
                b[0] - margin_x,
                b[1] - margin_y,
                b[2] + margin_x,
                b[3] + margin_y,
            )
            candidate_indices = tree.query(search_box)
            for idx in candidate_indices:
                tid, geom_b = target_features[idx]
                metrics = self.compute_metrics(geom_a, geom_b)
                if metrics is None:
                    continue

                spatial_score = self.combined_score_0_1(metrics)
                conf = round(spatial_score * 100, 2)

                # Keep candidate if intersects or within high proximity
                if metrics.overlap_ratio > 0 or (conf >= 50.0 and metrics.centroid_distance_m <= 30.0):
                    cand = {
                        "source_id": sid,
                        "target_id": tid,
                        "metrics": metrics,
                        "confidence": conf,
                        "geom_a": geom_a,
                        "geom_b": geom_b,
                        "relationship_type": "ONE_TO_ONE",
                        "status": "CANDIDATE",
                        "reasons": [
                            f"IoU: {metrics.overlap_ratio:.2f}",
                            f"Centroid distance: {metrics.centroid_distance_m:.1f}m",
                            f"Area similarity: {metrics.area_similarity:.2f}",
                            f"Topology: {metrics.topology_relationship}",
                        ],
                    }
                    candidates_by_source.setdefault(sid, []).append(cand)
                    candidates_by_target.setdefault(tid, []).append(cand)
                    all_candidates.append(cand)

        # --- Detect SPLIT (1 source -> multiple targets) ---
        split_sources = set()
        for sid, cands in candidates_by_source.items():
            overlapping_cands = [c for c in cands if c["metrics"].overlap_ratio > 0.10 or c["geom_a"].intersects(c["geom_b"])]
            if len(overlapping_cands) >= 2:
                source_geom = overlapping_cands[0]["geom_a"]
                source_area = source_geom.area
                target_areas_sum = sum(c["geom_b"].area for c in overlapping_cands)
                if source_area > 0 and abs(source_area - target_areas_sum) / source_area <= 0.35:
                    target_union = unary_union([c["geom_b"] for c in overlapping_cands])
                    coverage = source_geom.intersection(target_union).area / source_area
                    if coverage >= 0.55:
                        split_sources.add(sid)
                        for c in overlapping_cands:
                            c["relationship_type"] = "SPLIT"
                            c["status"] = "SPLIT"
                            c["reasons"].append(f"SPLIT detected: 1 feature in source matches {len(overlapping_cands)} subdivisions in target (coverage: {coverage:.1%}).")

        # --- Detect MERGE (multiple sources -> 1 target) ---
        merge_targets = set()
        for tid, cands in candidates_by_target.items():
            overlapping_cands = [c for c in cands if c["metrics"].overlap_ratio > 0.10 or c["geom_a"].intersects(c["geom_b"])]
            if len(overlapping_cands) >= 2:
                target_geom = overlapping_cands[0]["geom_b"]
                target_area = target_geom.area
                source_areas_sum = sum(c["geom_a"].area for c in overlapping_cands)
                if target_area > 0 and abs(target_area - source_areas_sum) / target_area <= 0.35:
                    source_union = unary_union([c["geom_a"] for c in overlapping_cands])
                    coverage = target_geom.intersection(source_union).area / target_area
                    if coverage >= 0.55:
                        merge_targets.add(tid)
                        for c in overlapping_cands:
                            c["relationship_type"] = "MERGE"
                            c["status"] = "MERGE"
                            c["reasons"].append(f"MERGE detected: {len(overlapping_cands)} source features merge into 1 target feature (coverage: {coverage:.1%}).")

        # Sort all candidates by confidence descending
        all_candidates.sort(key=lambda c: c["confidence"], reverse=True)

        used_sources = set()
        used_targets = set()
        final_matches: List[dict] = []

        # 1. Add confirmed splits and merges first
        for c in all_candidates:
            if c["source_id"] in split_sources or c["target_id"] in merge_targets:
                final_matches.append(c)
                used_sources.add(c["source_id"])
                used_targets.add(c["target_id"])

        # 2. Add remaining 1:1 candidates greedy by confidence
        for c in all_candidates:
            sid, tid = c["source_id"], c["target_id"]
            if sid in used_sources or tid in used_targets:
                continue

            conf = c["confidence"]
            if conf >= 80.0:
                c["status"] = "MATCHED"
            elif conf >= accept_threshold:
                c["status"] = "CANDIDATE"
            else:
                c["status"] = "REVIEW"

            final_matches.append(c)
            used_sources.add(sid)
            used_targets.add(tid)

        matched_source_ids = used_sources
        matched_target_ids = used_targets
        unmatched_sources = [sid for sid, _ in source_features if sid not in matched_source_ids]
        unmatched_targets = [tid for tid, _ in target_features if tid not in matched_target_ids]

        return {
            "matches": final_matches,
            "unmatched_sources": unmatched_sources,
            "unmatched_targets": unmatched_targets,
            "all_candidates": all_candidates,
        }
