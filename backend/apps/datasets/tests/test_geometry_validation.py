import pytest
from shapely.geometry import Polygon
from apps.datasets.services.geometry_validation_service import GeometryValidationService


def test_valid_polygon_passes():
    svc = GeometryValidationService()
    square = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    report = svc.validate_polygon(square)
    assert report["valid"] is True


def test_self_intersecting_polygon_flagged_and_repaired():
    svc = GeometryValidationService()
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])  # classic self-intersecting bowtie
    report = svc.validate_polygon(bowtie)
    assert report["valid"] is False

    repaired, applied, method = svc.safe_repair(bowtie)
    assert applied is True
    assert repaired.is_valid


def test_duplicate_detection():
    svc = GeometryValidationService()
    a = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    b = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    c = Polygon([(100, 100), (105, 100), (105, 105), (100, 105)])
    dupes = svc.find_duplicates([(1, a), (2, b), (3, c)])
    assert len(dupes) == 1
    assert {dupes[0]["feature_a"], dupes[0]["feature_b"]} == {1, 2}


def test_overlap_detection():
    svc = GeometryValidationService()
    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    b = Polygon([(5, 5), (15, 5), (15, 15), (5, 15)])  # overlaps a
    c = Polygon([(100, 100), (110, 100), (110, 110), (100, 110)])  # disjoint
    overlaps = svc.find_overlaps([(1, a), (2, b), (3, c)])
    assert len(overlaps) == 1
    assert overlaps[0]["overlap_area"] > 0
