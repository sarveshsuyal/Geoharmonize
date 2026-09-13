from apps.harmonization.services.confidence_service import ConfidenceService, ConfidenceFactors


def test_high_confidence_classification():
    svc = ConfidenceService(thresholds={"HIGH": 90, "MEDIUM": 70})
    factors = ConfidenceFactors(
        spatial_overlap=0.95, geometry_similarity=0.9, attribute_similarity=1.0,
        source_reliability=0.9, positional_accuracy=0.95, transformation_quality=1.0,
        cross_source_consistency=0.9,
    )
    score = svc.score(factors)
    assert score > 90
    assert svc.classify(score) == "HIGH"


def test_low_confidence_classification():
    svc = ConfidenceService()
    factors = ConfidenceFactors(
        spatial_overlap=0.1, geometry_similarity=0.2, attribute_similarity=0.1,
        source_reliability=0.3, positional_accuracy=0.1,
    )
    score = svc.score(factors)
    assert svc.classify(score) == "LOW"


def test_score_never_exceeds_bounds():
    svc = ConfidenceService()
    factors = ConfidenceFactors(1, 1, 1, 1, 1, 1, 1)
    score = svc.score(factors)
    assert 0 <= score <= 100
