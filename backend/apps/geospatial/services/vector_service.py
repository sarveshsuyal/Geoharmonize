"""
Imports a validated vector Dataset's features into the canonical PostGIS-backed
tables (Parcel, Building, Road, Utility) based on dataset_type, reprojecting into
the project's target CRS along the way, computing metric measurements, and ensuring
valid PostGIS SRID storage.
"""
import logging

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon, MultiLineString, LineString

from apps.datasets.services.vector_io import open_vector_source
from .crs_service_bridge import reproject_wkt
from .geometry_validation_service_bridge import validate_and_maybe_repair

logger = logging.getLogger("geoharmonize")


class VectorImportService:

    def import_dataset(self, dataset) -> dict:
        from shapely.geometry import shape
        from apps.parcels.models import Parcel, Building, Road, Utility

        target_crs = dataset.target_crs or settings.GEOHARMONIZE["PROJECT_TARGET_CRS"]
        original_crs = dataset.original_crs or "EPSG:4326"
        created, repaired, skipped = 0, 0, 0

        with open_vector_source(dataset.file.path) as src:
            for feat in src:
                geom = feat.get("geometry")
                props = dict(feat.get("properties", {}) or {})
                if not geom:
                    skipped += 1
                    continue

                try:
                    shp_geom = shape(geom)
                    if shp_geom.is_empty:
                        skipped += 1
                        continue

                    # Validate and safe repair
                    report, shp_geom, was_repaired = validate_and_maybe_repair(shp_geom)
                    if was_repaired:
                        repaired += 1
                    if not report["valid"] and any(i["severity"] == "CRITICAL" for i in report["issues"]):
                        skipped += 1
                        continue

                    # Reproject to metric target CRS for accurate area measurement
                    area_sqm = None
                    if original_crs and original_crs != target_crs:
                        try:
                            projected_shp = reproject_wkt(shp_geom, original_crs, target_crs)
                            area_sqm = projected_shp.area if hasattr(projected_shp, "area") else None
                        except Exception:
                            area_sqm = shp_geom.area if hasattr(shp_geom, "area") else None
                    else:
                        area_sqm = shp_geom.area if hasattr(shp_geom, "area") else None

                    # Transform to WGS84 (EPSG:4326) for standardized PostGIS storage and Leaflet display
                    if original_crs and original_crs != "EPSG:4326":
                        try:
                            wgs_shp = reproject_wkt(shp_geom, original_crs, "EPSG:4326")
                        except Exception:
                            wgs_shp = shp_geom
                    else:
                        wgs_shp = shp_geom

                    geos_geom = GEOSGeometry(wgs_shp.wkt, srid=4326)
                    self._route_to_model(dataset, geos_geom, props, area_sqm, Parcel, Building, Road, Utility)
                    created += 1

                except Exception as e:
                    logger.warning("Skipping malformed feature in %s: %s", dataset.name, e)
                    skipped += 1
                    continue

        return {
            "imported": created,
            "auto_repaired": repaired,
            "skipped": skipped,
            "target_crs": target_crs,
        }

    def _route_to_model(self, dataset, geom, props, area_sqm, Parcel, Building, Road, Utility):
        dt = dataset.dataset_type
        geom_type = geom.geom_type

        # Ensure correct multi-geometry types for PostGIS fields
        if geom_type == "Polygon":
            geom = MultiPolygon(geom)
        elif geom_type == "LineString":
            geom = MultiLineString(geom)

        if dt == "BUILDING" or (geom_type in ("Polygon", "MultiPolygon") and dt in ("MUNICIPAL",)):
            if dt == "BUILDING":
                b = Building.objects.create(
                    geometry=geom,
                    source_dataset=dataset,
                    footprint_id=str(props.get("id") or props.get("building_id") or ""),
                    attributes=props,
                )
                return b

        if dt == "ROAD" or (geom_type in ("LineString", "MultiLineString") and dt not in ("UTILITY",)):
            r = Road.objects.create(
                geometry=geom,
                source_dataset=dataset,
                road_id=str(props.get("road_id") or props.get("id") or ""),
                attributes=props,
            )
            return r

        if dt == "UTILITY":
            u = Utility.objects.create(
                geometry=geom,
                source_dataset=dataset,
                utility_type=str(props.get("type", "OTHER")),
                attributes=props,
            )
            return u

        # Default: parcels (cadastral, drone, municipal, revenue polygons)
        from apps.harmonization.services.attribute_mapping import map_to_canonical_attributes
        canonical = map_to_canonical_attributes(props, dataset.dataset_type)

        parcel_id = str(
            canonical.get("parcel_id")
            or props.get("parcel_id")
            or props.get("candidate_id")
            or props.get("id")
            or f"P-{dataset.id}-{Parcel.objects.count() + 1}"
        )
        survey_number = str(canonical.get("survey_number") or props.get("survey_no") or props.get("khasra_no") or "")
        property_ref = str(canonical.get("property_id") or props.get("property_no") or "")
        land_use = str(canonical.get("land_use") or props.get("landuse") or props.get("land_use") or "")

        parcel = Parcel.objects.create(
            geometry=geom,
            parcel_id=parcel_id,
            survey_number=survey_number,
            property_reference=property_ref,
            area=area_sqm if area_sqm is not None else geom.area,
            land_use=land_use,
            raw_attributes=props,
            confidence_score=0,
            validation_status="VALID",
        )
        parcel.source_datasets.add(dataset)
        return parcel
