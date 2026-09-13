"""
Compares two datasets/years and classifies features as ADDED / REMOVED /
MODIFIED / UNCHANGED using real geometry comparison (vector-vs-vector) or
image differencing (raster-vs-raster). This is a GEOSPATIAL/CV comparison
routine, not a trained ML model.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class ChangeRecord:
    feature_id_before: object
    feature_id_after: object
    change_type: str  # ADDED | REMOVED | MODIFIED | UNCHANGED
    geometry_before_wkt: str = None
    geometry_after_wkt: str = None
    iou: float = None


class VectorChangeDetector:
    UNCHANGED_IOU_THRESHOLD = 0.98
    MODIFIED_IOU_THRESHOLD = 0.5  # below this but still matched -> MODIFIED; unmatched -> ADDED/REMOVED

    def compare(self, before_features: list, after_features: list) -> List[ChangeRecord]:
        """before_features / after_features: list of (id, shapely_geom)."""
        from apps.harmonization.services.matching_service import MatchingService
        ms = MatchingService()
        match_result = ms.find_best_matches(before_features, after_features, accept_threshold=0)

        records = []
        before_by_id = dict(before_features)
        after_by_id = dict(after_features)

        for m in match_result["matches"]:
            iou = m["metrics"].overlap_ratio
            if iou >= self.UNCHANGED_IOU_THRESHOLD:
                change = "UNCHANGED"
            else:
                change = "MODIFIED"
            records.append(ChangeRecord(
                feature_id_before=m["source_id"], feature_id_after=m["target_id"],
                change_type=change,
                geometry_before_wkt=before_by_id[m["source_id"]].wkt,
                geometry_after_wkt=after_by_id[m["target_id"]].wkt,
                iou=iou,
            ))

        for fid in match_result["unmatched_sources"]:
            records.append(ChangeRecord(feature_id_before=fid, feature_id_after=None, change_type="REMOVED",
                                         geometry_before_wkt=before_by_id[fid].wkt))
        for fid in match_result["unmatched_targets"]:
            records.append(ChangeRecord(feature_id_before=None, feature_id_after=fid, change_type="ADDED",
                                         geometry_after_wkt=after_by_id[fid].wkt))
        return records
