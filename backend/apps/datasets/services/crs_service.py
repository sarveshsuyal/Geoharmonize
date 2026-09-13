"""
CRS detection & normalization service.

Responsible for:
  - Detecting the CRS of an uploaded vector/raster file (via GDAL/OGR/rasterio).
  - Reprojecting a dataset's geometries into the project's target CRS.
  - Never silently assuming a default CRS - if detection fails, the caller
    must ask the user to specify one (see Dataset.processing_status = NEEDS_CRS).
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("geoharmonize")


@dataclass
class CRSDetectionResult:
    crs: Optional[str]          # e.g. "EPSG:4326", or None if undetectable
    confidence: str             # "DETECTED" | "UNKNOWN"
    raw_wkt: Optional[str] = None


class CRSService:
    """
    Wraps pyproj/GDAL. Import is deferred so the module can be imported
    (e.g. for unit-testing pure logic) even in environments without GDAL bindings.
    """

    def detect_vector_crs(self, filepath: str) -> CRSDetectionResult:
        try:
            import fiona
        except ImportError as e:
            raise RuntimeError(
                "fiona/GDAL is not installed. Install the geospatial dependencies "
                "in requirements.txt (this requires libgdal on the OS)."
            ) from e

        from .vector_io import open_vector_source

        with open_vector_source(filepath) as src:
            crs = src.crs
            if not crs:
                return CRSDetectionResult(crs=None, confidence="UNKNOWN")
            epsg = crs.to_epsg() if hasattr(crs, "to_epsg") else None
            if epsg:
                return CRSDetectionResult(crs=f"EPSG:{epsg}", confidence="DETECTED", raw_wkt=str(crs))
            return CRSDetectionResult(crs=None, confidence="UNKNOWN", raw_wkt=str(crs))

    def detect_raster_crs(self, filepath: str) -> CRSDetectionResult:
        try:
            import rasterio
        except ImportError as e:
            raise RuntimeError("rasterio/GDAL is not installed.") from e

        with rasterio.open(filepath) as src:
            if src.crs is None:
                return CRSDetectionResult(crs=None, confidence="UNKNOWN")
            epsg = src.crs.to_epsg()
            if epsg:
                return CRSDetectionResult(crs=f"EPSG:{epsg}", confidence="DETECTED", raw_wkt=str(src.crs))
            return CRSDetectionResult(crs=None, confidence="UNKNOWN", raw_wkt=str(src.crs))

    def reproject_geometry(self, geometry, source_crs: str, target_crs: str):
        """Reproject a Shapely geometry from source_crs to target_crs."""
        from pyproj import Transformer
        from shapely.ops import transform as shp_transform

        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        return shp_transform(transformer.transform, geometry)

    def transform_status(self, original_crs: Optional[str], target_crs: str) -> str:
        if not original_crs:
            return "PENDING_CRS_SELECTION"
        if original_crs == target_crs:
            return "NO_TRANSFORM_NEEDED"
        return "SUCCESSFULLY_TRANSFORMED"
