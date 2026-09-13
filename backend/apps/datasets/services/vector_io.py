"""
Safe vector source reader supporting GeoJSON, GeoPackage, and Shapefile ZIP archives.
Handles archive security checks (zip-bomb, path traversal) and provides a clean context manager.
"""
import os
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
import logging

logger = logging.getLogger("geoharmonize")

MAX_UNCOMPRESSED_ZIP_SIZE = 500 * 1024 * 1024  # 500 MB


@contextmanager
def open_vector_source(filepath: str):
    """
    Context manager yielding (fiona_src, temp_dir_path).
    Automatically cleans up temporary directories if a ZIP was unpacked.
    """
    import fiona

    ext = os.path.splitext(filepath)[1].lower()
    temp_dir = None

    try:
        if ext == ".zip":
            temp_dir = tempfile.mkdtemp(prefix="geoharmonize_shp_")
            with zipfile.ZipFile(filepath, "r") as zf:
                total_size = 0
                for info in zf.infolist():
                    total_size += info.file_size
                    if total_size > MAX_UNCOMPRESSED_ZIP_SIZE:
                        raise ValueError("ZIP archive exceeds safe extraction limit (500 MB).")
                    filename = info.filename
                    if filename.startswith("/") or filename.startswith("\\") or ".." in filename:
                        raise ValueError(f"ZIP archive contains unsafe relative path: {filename}")
                zf.extractall(temp_dir)

            # Find .shp file or .geojson in extracted directory
            target_file = None
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    if f.lower().endswith(".shp"):
                        target_file = os.path.join(root, f)
                        break
                    elif f.lower().endswith((".geojson", ".json", ".gpkg")) and not target_file:
                        target_file = os.path.join(root, f)
                if target_file and target_file.lower().endswith(".shp"):
                    break

            if not target_file:
                raise ValueError("No valid Shapefile (.shp), GeoPackage (.gpkg), or GeoJSON found in archive.")

            with fiona.open(target_file) as src:
                yield src
        else:
            with fiona.open(filepath) as src:
                yield src
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning("Failed to remove temp dir %s: %s", temp_dir, e)
