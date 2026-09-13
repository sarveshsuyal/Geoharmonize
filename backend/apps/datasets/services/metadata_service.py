"""
Extracts descriptive metadata from an uploaded file: geometry type, feature count,
bounding box (vector), CRS, invalid/empty counts, and attribute schema.
"""
import logging
from .vector_io import open_vector_source

logger = logging.getLogger("geoharmonize")


class MetadataService:
    VECTOR_EXTENSIONS = {".geojson", ".json", ".zip", ".kml", ".kmz", ".csv", ".gpkg", ".shp"}
    RASTER_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}

    def is_raster(self, filename: str) -> bool:
        ext = "." + filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        return ext in self.RASTER_EXTENSIONS

    def extract_vector_metadata(self, filepath: str) -> dict:
        from shapely.geometry import shape

        with open_vector_source(filepath) as src:
            geom_types = set()
            count = 0
            null_count = 0
            empty_count = 0
            invalid_count = 0
            valid_count = 0
            seen_ids = set()
            duplicate_id_count = 0

            minx = miny = float("inf")
            maxx = maxy = float("-inf")

            for feat in src:
                count += 1
                fid = feat.get("id") or feat.get("properties", {}).get("id") or feat.get("properties", {}).get("parcel_id")
                if fid is not None:
                    if fid in seen_ids:
                        duplicate_id_count += 1
                    else:
                        seen_ids.add(fid)

                geom = feat.get("geometry")
                if not geom:
                    null_count += 1
                    continue

                g_type = geom.get("type", "Unknown")
                geom_types.add(g_type)

                try:
                    g = shape(geom)
                    if g.is_empty:
                        empty_count += 1
                        continue

                    if not g.is_valid:
                        invalid_count += 1
                    else:
                        valid_count += 1

                    b = g.bounds
                    minx, miny = min(minx, b[0]), min(miny, b[1])
                    maxx, maxy = max(maxx, b[2]), max(maxy, b[3])
                except Exception as e:
                    logger.debug("Failed parsing feature geometry: %s", e)
                    invalid_count += 1

            bbox = [minx, miny, maxx, maxy] if (valid_count > 0 and minx != float("inf")) else None

            # Inspect schema
            schema_props = src.schema.get("properties", {}) or {}
            attributes = [{"name": name, "type": str(prop_type)} for name, prop_type in schema_props.items()]

            # Detect CRS representation
            crs_str = None
            if src.crs:
                epsg = src.crs.to_epsg() if hasattr(src.crs, "to_epsg") else None
                crs_str = f"EPSG:{epsg}" if epsg else str(src.crs)

            return {
                "driver": src.driver,
                "layer_geometry_types": sorted(list(geom_types)) or [str(src.schema.get("geometry"))],
                "feature_count": count,
                "valid_geometry_count": valid_count,
                "invalid_geometry_count": invalid_count,
                "empty_geometry_count": empty_count,
                "null_geometry_count": null_count,
                "duplicate_id_count": duplicate_id_count,
                "bbox": bbox,
                "crs": crs_str,
                "field_names": list(schema_props.keys()),
                "attributes": attributes,
            }

    def extract_raster_metadata(self, filepath: str) -> dict:
        import rasterio

        with rasterio.open(filepath) as src:
            return {
                "driver": src.driver,
                "width": src.width,
                "height": src.height,
                "band_count": src.count,
                "dtype": src.dtypes[0] if src.dtypes else None,
                "bbox": list(src.bounds),
                "resolution": list(src.res),
                "nodata": src.nodata,
            }

    def infer_primary_geometry_type(self, geom_types: list) -> str:
        if not geom_types:
            return "UNKNOWN"
        joined = ",".join(geom_types).upper()
        if "MULTIPOLYGON" in joined:
            return "MULTIPOLYGON"
        if "POLYGON" in joined:
            return "POLYGON"
        if "LINESTRING" in joined:
            return "LINESTRING"
        if "POINT" in joined:
            return "POINT"
        return "UNKNOWN"
