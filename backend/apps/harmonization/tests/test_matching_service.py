import math
import pytest
from shapely.geometry import box
from apps.harmonization.services.matching_service import MatchingService


def test_identical_polygons_score_near_100():
    svc = MatchingService()
    a = box(0, 0, 20, 15)
    b = box(0, 0, 20, 15)
    metrics = svc.compute_metrics(a, b)
    assert metrics.overlap_ratio == pytest.approx(1.0)
    score = svc.combined_score_0_1(metrics) * 100
    assert score > 95


def test_shifted_polygon_scores_high_but_not_perfect():
    svc = MatchingService()
    a = box(0, 0, 20, 15)
    b = box(0.5, 0.3, 20.4, 15.3)  # ~0.5-2m equivalent shift
    metrics = svc.compute_metrics(a, b)
    score = svc.combined_score_0_1(metrics) * 100
    assert 70 < score < 100
    assert metrics.overlap_ratio > 0.8


def test_disjoint_polygons_score_zero_overlap():
    svc = MatchingService()
    a = box(0, 0, 20, 15)
    b = box(1000, 1000, 1010, 1010)
    metrics = svc.compute_metrics(a, b)
    assert metrics.overlap_ratio == 0.0


def test_find_best_matches_is_one_to_one():
    svc = MatchingService()
    source = [(1, box(0, 0, 10, 10)), (2, box(100, 100, 110, 110))]
    target = [(10, box(0.1, 0.1, 10.1, 10.1)), (20, box(100.1, 100.1, 110.1, 110.1))]
    result = svc.find_best_matches(source, target, accept_threshold=50)
    assert len(result["matches"]) == 2
    matched_pairs = {(m["source_id"], m["target_id"]) for m in result["matches"]}
    assert (1, 10) in matched_pairs
    assert (2, 20) in matched_pairs
    assert not result["unmatched_sources"]
    assert not result["unmatched_targets"]


def test_find_best_matches_reports_unmatched():
    svc = MatchingService()
    source = [(1, box(0, 0, 10, 10))]
    target = [(10, box(500, 500, 510, 510))]
    result = svc.find_best_matches(source, target, accept_threshold=50)
    assert result["matches"] == []
    assert result["unmatched_sources"] == [1]
    assert result["unmatched_targets"] == [10]
