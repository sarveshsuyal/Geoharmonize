from apps.conflicts.services.conflict_detection_service import ConflictDetectionService


def test_boundary_severity_bands():
    svc = ConflictDetectionService()
    assert svc._severity_from_boundary_diff(0.1) == "LOW"
    assert svc._severity_from_boundary_diff(0.5) == "MEDIUM"
    assert svc._severity_from_boundary_diff(1.5) == "HIGH"
    assert svc._severity_from_boundary_diff(5.0) == "CRITICAL"


def test_area_severity_bands():
    svc = ConflictDetectionService()
    assert svc._severity_from_area_diff(2) == "LOW"
    assert svc._severity_from_area_diff(10) == "MEDIUM"
    assert svc._severity_from_area_diff(20) == "HIGH"
    assert svc._severity_from_area_diff(40) == "CRITICAL"
