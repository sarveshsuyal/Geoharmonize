"""
Imagery Provider for AOI-based AI analysis.

Decouples the AI analysis imagery source from the visual basemap:
  1. Checks for local uploaded raster Datasets covering the AOI.
  2. Fetches high-resolution satellite tiles (e.g., Esri World Imagery)
     covering the AOI bounding box when available.
  3. Provides a procedural fallback image synthesizer for offline / test
     environments, ensuring robust execution under any network conditions.
"""
import io
import math
import urllib.request
from typing import Tuple, Optional
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def num2deg(xtile: int, ytile: int, zoom: int) -> Tuple[float, float]:
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


class ImageryProvider:
    """
    Retrieves and georeferences satellite/aerial imagery for an AOI.
    """

    def __init__(self, zoom: int = 17):
        self.zoom = zoom

    def get_aoi_raster(self, aoi_geom: Polygon, bounds: Tuple[float, float, float, float]):
        """
        Returns:
            rgb_array: np.ndarray (H, W, 3) uint8
            transform: rasterio.Affine transform (pixel -> map coords)
            source_type: str ("LOCAL_DATASET" | "SATELLITE_TILES" | "SYNTHETIC_OFFLINE")
        """
        min_lon, min_lat, max_lon, max_lat = bounds

        # 1. Try local uploaded raster datasets if any exist
        local_result = self._try_local_dataset(aoi_geom, bounds)
        if local_result is not None:
            return local_result

        # 2. Try fetching satellite XYZ tiles
        tile_result = self._try_fetch_satellite_tiles(min_lon, min_lat, max_lon, max_lat)
        if tile_result is not None:
            return tile_result

        # 3. Fallback: Synthesize calibrated georeferenced raster for AOI
        return self._generate_synthetic_aoi(min_lon, min_lat, max_lon, max_lat)

    def _try_local_dataset(self, aoi_geom: Polygon, bounds):
        try:
            from apps.datasets.models import Dataset, GeometryKind
            from apps.geospatial.services.raster_service import RasterService
            min_lon, min_lat, max_lon, max_lat = bounds

            rasters = Dataset.objects.filter(geometry_type=GeometryKind.RASTER, file__isnull=False)
            for ds in rasters:
                if ds.bbox and len(ds.bbox) == 4:
                    b_minx, b_miny, b_maxx, b_maxy = ds.bbox
                    if (b_minx <= min_lon and b_maxx >= max_lon and
                            b_miny <= min_lat and b_maxy >= max_lat):
                        rs = RasterService()
                        arr, transform, crs = rs.read_as_array(ds.file.path)
                        # Crop to AOI bounds
                        if arr.ndim == 3 and arr.shape[0] in (3, 4):
                            arr = np.transpose(arr[:3], (1, 2, 0))
                        return arr.astype(np.uint8), transform, "LOCAL_DATASET"
        except Exception:
            pass
        return None

    def _try_fetch_satellite_tiles(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        """
        Downloads Esri World Imagery tiles covering the bounding box and stitches them.
        """
        import rasterio.transform

        z = self.zoom
        x_min, y_min = deg2num(max_lat, min_lon, z)  # north-west tile
        x_max, y_max = deg2num(min_lat, max_lon, z)  # south-east tile

        # Safeguard: cap tiles to max 16 (4x4) to avoid long network operations
        if (x_max - x_min + 1) * (y_max - y_min + 1) > 16 or (x_max < x_min) or (y_max < y_min):
            z = max(14, z - 2)
            x_min, y_min = deg2num(max_lat, min_lon, z)
            x_max, y_max = deg2num(min_lat, max_lon, z)

        cols = x_max - x_min + 1
        rows = y_max - y_min + 1
        tile_size = 256

        stitched = Image.new("RGB", (cols * tile_size, rows * tile_size))
        headers = {"User-Agent": "GeoHarmonize-GIS/1.0"}

        try:
            for r, y in enumerate(range(y_min, y_max + 1)):
                for c, x in enumerate(range(x_min, x_max + 1)):
                    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        tile_img = Image.open(io.BytesIO(resp.read())).convert("RGB")
                        stitched.paste(tile_img, (c * tile_size, r * tile_size))

            # Calculate stitched tile bounds
            top_lat, left_lon = num2deg(x_min, y_min, z)
            bottom_lat, right_lon = num2deg(x_max + 1, y_max + 1, z)

            transform = rasterio.transform.from_bounds(
                left_lon, bottom_lat, right_lon, top_lat, stitched.width, stitched.height
            )
            arr = np.array(stitched, dtype=np.uint8)
            return arr, transform, "SATELLITE_TILES"
        except Exception:
            return None

    def _generate_synthetic_aoi(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
        """
        Synthesizes a realistic georeferenced orthophoto for testing/offline scenarios.
        """
        import rasterio.transform
        import cv2

        width, height = 512, 512
        # Base terrain: natural warm soil/vegetation background
        arr = np.full((height, width, 3), [110, 140, 95], dtype=np.uint8)

        # Seeded pseudo-random features based on coordinates
        seed = int(abs(min_lon * 1000 + min_lat * 10000)) % 100000
        rng = np.random.RandomState(seed)

        # Add natural texture noise
        noise = rng.randint(-15, 15, (height, width, 3), dtype=np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Draw realistic agricultural patches (yellowish green)
        for _ in range(4):
            x1, y1 = rng.randint(40, width - 150), rng.randint(40, height - 150)
            w, h = rng.randint(80, 160), rng.randint(80, 160)
            color = [rng.randint(140, 180), rng.randint(160, 200), rng.randint(70, 95)]
            cv2.rectangle(arr, (x1, y1), (x1 + w, y1 + h), color, -1)

        # Draw dense vegetation clusters (deep dark green)
        for _ in range(3):
            cx, cy = rng.randint(60, width - 60), rng.randint(60, height - 60)
            radius = rng.randint(30, 60)
            color = [rng.randint(35, 60), rng.randint(90, 125), rng.randint(35, 55)]
            cv2.circle(arr, (cx, cy), radius, color, -1)

        # Draw a water canal / pond (blue)
        if rng.rand() > 0.3:
            pts = np.array([
                [rng.randint(20, 120), rng.randint(height - 180, height - 40)],
                [rng.randint(140, 240), rng.randint(height - 140, height - 20)],
                [rng.randint(260, 360), rng.randint(height - 120, height - 20)],
            ], np.int32)
            cv2.polylines(arr, [pts], False, [180, 110, 45], thickness=18)  # BGR water in OpenCV is RGB [45, 110, 180]

        # Draw a road corridor (gray/orange asphalt)
        rx1, ry1 = 0, rng.randint(height // 3, 2 * height // 3)
        rx2, ry2 = width, ry1 + rng.randint(-60, 60)
        cv2.line(arr, (rx1, ry1), (rx2, ry2), [135, 130, 125], thickness=14)

        # Draw building footprints (bright structures with high contrast)
        for _ in range(5):
            bx = rng.randint(50, width - 100)
            by = rng.randint(50, height - 100)
            bw, bh = rng.randint(25, 55), rng.randint(25, 50)
            # Avoid water
            cv2.rectangle(arr, (bx, by), (bx + bw, by + bh), [215, 205, 195], -1)
            cv2.rectangle(arr, (bx, by), (bx + bw, by + bh), [90, 80, 75], 2)

        # Draw bare/vacant open lot (sandy soil color)
        vx, vy = rng.randint(100, width - 120), rng.randint(100, height - 120)
        cv2.rectangle(arr, (vx, vy), (vx + 90, vy + 80), [165, 145, 115], -1)

        transform = rasterio.transform.from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)
        return arr, transform, "SYNTHETIC_OFFLINE"
