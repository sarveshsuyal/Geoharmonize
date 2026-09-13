"""
Ingestion orchestration: validates the uploaded file, extracts metadata,
detects CRS, and creates/updates the Dataset record. Delegates actual
geo-parsing to MetadataService / CRSService - this file only orchestrates.
"""
import logging
import os
import time
import zipfile

from django.conf import settings

from ..models import Dataset, ProcessingStatus, GeometryKind, ProcessingLog
from .metadata_service import MetadataService
from .crs_service import CRSService

logger = logging.getLogger("geoharmonize")

ALLOWED_EXTENSIONS = {
    ".geojson", ".json", ".zip", ".tif", ".tiff", ".kml", ".kmz", ".csv", ".png", ".jpg", ".jpeg",
    ".gpkg", ".shp",
}


class IngestionError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


class IngestionService:
    def __init__(self):
        self.metadata_service = MetadataService()
        self.crs_service = CRSService()

    def validate_extension(self, filename: str):
        ext = "." + filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise IngestionError(
                "UNSUPPORTED_FORMAT",
                f"'{ext}' is not a supported format. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        return ext

    def validate_size(self, size_bytes: int):
        max_bytes = settings.GEOHARMONIZE["MAX_UPLOAD_SIZE_MB"] * 1024 * 1024
        if size_bytes > max_bytes:
            raise IngestionError(
                "FILE_TOO_LARGE",
                f"File exceeds the {settings.GEOHARMONIZE['MAX_UPLOAD_SIZE_MB']}MB upload limit.",
            )

    def validate_zip_is_shapefile_or_safe(self, filepath: str):
        """Basic zip-bomb / path traversal guard for shapefile ZIPs."""
        with zipfile.ZipFile(filepath) as zf:
            total_uncompressed = sum(i.file_size for i in zf.infolist())
            if total_uncompressed > 500 * 1024 * 1024:
                raise IngestionError("ZIP_TOO_LARGE", "Archive expands beyond the allowed limit.")
            for name in zf.namelist():
                if name.startswith("/") or ".." in name:
                    raise IngestionError("UNSAFE_ARCHIVE", "Archive contains unsafe file paths.")

    def process_new_dataset(self, dataset: Dataset) -> Dataset:
        """
        Runs steps 1-11 of the ingestion pipeline against an already-saved
        Dataset row (file already stored by the DRF view/serializer).
        """
        start = time.time()
        dataset.processing_status = ProcessingStatus.VALIDATING
        dataset.save(update_fields=["processing_status"])

        filepath = dataset.file.path
        filename = dataset.original_filename or os.path.basename(filepath)

        try:
            self.validate_extension(filename)
            self.validate_size(os.path.getsize(filepath))
            if filename.lower().endswith(".zip"):
                self.validate_zip_is_shapefile_or_safe(filepath)

            is_raster = self.metadata_service.is_raster(filename)

            if is_raster:
                meta = self.metadata_service.extract_raster_metadata(filepath)
                crs_result = self.crs_service.detect_raster_crs(filepath)
                dataset.geometry_type = GeometryKind.RASTER
                dataset.feature_count = None
            else:
                meta = self.metadata_service.extract_vector_metadata(filepath)
                crs_result = self.crs_service.detect_vector_crs(filepath)
                dataset.geometry_type = self.metadata_service.infer_primary_geometry_type(
                    meta.get("layer_geometry_types", [])
                )
                dataset.feature_count = meta.get("feature_count")

            dataset.metadata = meta
            dataset.bbox = meta.get("bbox")
            dataset.original_crs = crs_result.crs
            dataset.crs_confidence = crs_result.confidence
            dataset.target_crs = settings.GEOHARMONIZE["PROJECT_TARGET_CRS"]

            if crs_result.crs is None:
                dataset.processing_status = ProcessingStatus.NEEDS_CRS
                self._log(dataset, "crs_detection", "WARNING",
                          "CRS not detected. Manual CRS selection required before processing.")
            else:
                dataset.processing_status = ProcessingStatus.VALIDATED
                self._log(dataset, "crs_detection", "INFO", f"Detected CRS: {crs_result.crs}")

            dataset.error_message = ""
            dataset.save()
            self._log(dataset, "ingestion", "INFO", "Ingestion completed.",
                      duration_ms=int((time.time() - start) * 1000))
            return dataset

        except IngestionError as e:
            dataset.processing_status = ProcessingStatus.FAILED
            dataset.error_message = f"{e.code}: {e.message}"
            dataset.save(update_fields=["processing_status", "error_message"])
            self._log(dataset, "ingestion", "ERROR", dataset.error_message)
            raise
        except Exception as e:  # noqa: BLE001 - convert unexpected errors into a stored, visible failure
            logger.exception("Unexpected ingestion failure")
            dataset.processing_status = ProcessingStatus.FAILED
            dataset.error_message = f"UNEXPECTED_ERROR: {e}"
            dataset.save(update_fields=["processing_status", "error_message"])
            self._log(dataset, "ingestion", "ERROR", dataset.error_message)
            raise

    def set_manual_crs(self, dataset: Dataset, crs: str) -> Dataset:
        dataset.original_crs = crs
        dataset.crs_confidence = "USER_SPECIFIED"
        dataset.processing_status = ProcessingStatus.VALIDATED
        dataset.save()
        self._log(dataset, "crs_detection", "INFO", f"CRS manually set to {crs}")
        return dataset

    def _log(self, dataset, step, level, message, duration_ms=None):
        ProcessingLog.objects.create(
            dataset=dataset, step=step, level=level, message=message, duration_ms=duration_ms
        )
