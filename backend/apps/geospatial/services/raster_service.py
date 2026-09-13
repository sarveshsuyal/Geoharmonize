"""
Raster utilities shared by the AI/CV pipeline and change detection:
reading bands as numpy arrays, georeferencing pixel coordinates back to
map coordinates (so CV-detected features become real geometries), and
basic raster-to-raster image differencing for change detection.
"""
import numpy as np


class RasterService:

    def read_as_array(self, filepath: str):
        import rasterio
        with rasterio.open(filepath) as src:
            arr = src.read()
            transform = src.transform
            crs = src.crs
        return arr, transform, crs

    def pixel_to_map(self, transform, row: int, col: int):
        """Affine pixel->map coordinate transform (used to georeference CV contours)."""
        x, y = transform * (col, row)
        return x, y

    def pixel_polygon_to_map_polygon(self, transform, pixel_coords):
        """pixel_coords: list of (col, row) tuples from an OpenCV contour."""
        from shapely.geometry import Polygon
        mapped = [self.pixel_to_map(transform, row, col) for col, row in pixel_coords]
        if len(mapped) < 3:
            return None
        return Polygon(mapped)

    def align_shapes(self, arr_a: np.ndarray, arr_b: np.ndarray):
        """Crop both arrays to the same (smaller) shape so they can be diffed."""
        h = min(arr_a.shape[-2], arr_b.shape[-2])
        w = min(arr_a.shape[-1], arr_b.shape[-1])
        return arr_a[..., :h, :w], arr_b[..., :h, :w]

    def difference(self, arr_a: np.ndarray, arr_b: np.ndarray, threshold: int = 30) -> np.ndarray:
        """Simple absolute-difference change mask between two co-registered rasters."""
        a, b = self.align_shapes(arr_a, arr_b)
        if a.ndim == 3:
            a = a.mean(axis=0)
            b = b.mean(axis=0)
        diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
        return (diff > threshold).astype(np.uint8) * 255
