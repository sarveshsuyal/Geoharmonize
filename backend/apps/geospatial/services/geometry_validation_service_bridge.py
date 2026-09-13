def validate_and_maybe_repair(shapely_geom):
    from apps.datasets.services.geometry_validation_service import GeometryValidationService
    svc = GeometryValidationService()
    report = svc.validate_polygon(shapely_geom)
    if not report["valid"]:
        repaired, applied, method = svc.safe_repair(shapely_geom)
        if applied:
            return report, repaired, True
    return report, shapely_geom, False
