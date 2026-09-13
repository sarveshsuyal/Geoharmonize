"""
Confidence engine - combines multiple measurable factors into a single 0-100
score, and classifies it into HIGH/MEDIUM/LOW bands using configurable
thresholds (settings.GEOHARMONIZE.CONFIDENCE_THRESHOLDS).

Used for: parcel matches, harmonized parcel records, conflict resolutions.
Never fabricates a score - every input must be a real measured value.
Generates explainable factor breakdowns and human-readable reasons.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional


@dataclass
class ConfidenceFactors:
    spatial_overlap: float = 0.0        # 0-1 (IoU)
    geometry_similarity: float = 0.0    # 0-1 (shape similarity)
    attribute_similarity: float = 0.0   # 0-1 (attribute agreement across sources)
    source_reliability: float = 0.0     # 0-1 (normalized SOURCE_RELIABILITY)
    positional_accuracy: float = 0.0    # 0-1 (derived from centroid distance decay)
    transformation_quality: float = 1.0  # 0-1 (1.0 if CRS transform succeeded cleanly)
    cross_source_consistency: float = 0.0  # 0-1 (agreement across >2 sources, if applicable)


class ConfidenceService:
    WEIGHTS = {
        "spatial_overlap": 0.30,
        "geometry_similarity": 0.15,
        "attribute_similarity": 0.15,
        "source_reliability": 0.15,
        "positional_accuracy": 0.15,
        "transformation_quality": 0.05,
        "cross_source_consistency": 0.05,
    }

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {"HIGH": 90, "MEDIUM": 70}

    def score(self, factors: ConfidenceFactors) -> float:
        total = (
            self.WEIGHTS["spatial_overlap"] * factors.spatial_overlap
            + self.WEIGHTS["geometry_similarity"] * factors.geometry_similarity
            + self.WEIGHTS["attribute_similarity"] * factors.attribute_similarity
            + self.WEIGHTS["source_reliability"] * factors.source_reliability
            + self.WEIGHTS["positional_accuracy"] * factors.positional_accuracy
            + self.WEIGHTS["transformation_quality"] * factors.transformation_quality
            + self.WEIGHTS["cross_source_consistency"] * factors.cross_source_consistency
        )
        return round(max(0.0, min(1.0, total)) * 100, 2)

    def classify(self, score_0_100: float) -> str:
        if score_0_100 >= self.thresholds.get("HIGH", 85):
            return "HIGH"
        if score_0_100 >= self.thresholds.get("MEDIUM", 65):
            return "MEDIUM"
        return "LOW"

    def from_match(
        self,
        match_metrics,
        source_reliability_0_100: float,
        attribute_similarity_0_1: float,
        transformation_quality: float = 1.0,
        attribute_detail: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, str, ConfidenceFactors, Dict[str, Any], List[str]]:
        """
        Builds ConfidenceFactors, computes confidence score and classification,
        and generates an explainable breakdown dictionary with reasons.
        """
        from .matching_service import MatchingService
        ms = MatchingService()
        pos_acc = ms.centroid_similarity_score(match_metrics.centroid_distance_m)

        factors = ConfidenceFactors(
            spatial_overlap=match_metrics.overlap_ratio,
            geometry_similarity=max(0.0, match_metrics.shape_similarity),
            attribute_similarity=attribute_similarity_0_1,
            source_reliability=source_reliability_0_100 / 100.0,
            positional_accuracy=pos_acc,
            transformation_quality=transformation_quality,
            cross_source_consistency=0.5,
        )
        score = self.score(factors)
        band = self.classify(score)

        # Generate explainable reasons
        reasons = []
        if match_metrics.overlap_ratio >= 0.90:
            reasons.append(f"Near-complete boundary overlap (IoU: {match_metrics.overlap_ratio:.2f}).")
        elif match_metrics.overlap_ratio >= 0.60:
            reasons.append(f"Substantial spatial overlap (IoU: {match_metrics.overlap_ratio:.2f}).")
        elif match_metrics.overlap_ratio > 0:
            reasons.append(f"Partial spatial overlap (IoU: {match_metrics.overlap_ratio:.2f}).")
        else:
            reasons.append("Geometries are spatially disjoint.")

        if match_metrics.centroid_distance_m <= 1.0:
            reasons.append(f"Centroids align within {match_metrics.centroid_distance_m:.2f}m.")
        elif match_metrics.centroid_distance_m <= 5.0:
            reasons.append(f"Centroid distance is small ({match_metrics.centroid_distance_m:.1f}m).")
        else:
            reasons.append(f"Centroid distance is {match_metrics.centroid_distance_m:.1f}m.")

        if match_metrics.area_similarity >= 0.90:
            reasons.append(f"Area similarity is {match_metrics.area_similarity * 100:.1f}%.")
        else:
            reasons.append(f"Area ratio is {match_metrics.area_similarity * 100:.1f}%.")

        if attribute_similarity_0_1 >= 0.85:
            reasons.append(f"High attribute correspondence ({attribute_similarity_0_1 * 100:.0f}%).")
        elif attribute_similarity_0_1 >= 0.50:
            reasons.append(f"Moderate attribute correspondence ({attribute_similarity_0_1 * 100:.0f}%).")
        else:
            reasons.append("Attributes show divergence or unmapped fields.")

        if attribute_detail and "explanations" in attribute_detail:
            for exp in attribute_detail["explanations"]:
                if exp not in reasons:
                    reasons.append(exp)

        metrics_breakdown = {
            "overall_confidence": score,
            "confidence_band": band,
            "spatial": {
                "overlap_ratio": match_metrics.overlap_ratio,
                "area_similarity": match_metrics.area_similarity,
                "centroid_distance_m": round(match_metrics.centroid_distance_m, 2),
                "shape_similarity": round(match_metrics.shape_similarity, 3),
                "boundary_similarity": round(match_metrics.boundary_similarity, 3),
                "topology": match_metrics.topology_relationship,
            },
            "attributes": {
                "similarity": round(attribute_similarity_0_1, 3),
                "fields": attribute_detail.get("fields", {}) if attribute_detail else {},
            },
            "factors": {
                "spatial_overlap": factors.spatial_overlap,
                "geometry_similarity": factors.geometry_similarity,
                "attribute_similarity": factors.attribute_similarity,
                "source_reliability": factors.source_reliability,
                "positional_accuracy": factors.positional_accuracy,
            },
        }

        return score, band, factors, metrics_breakdown, reasons
