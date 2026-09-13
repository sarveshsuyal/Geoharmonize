"""Thin re-export so geospatial services can reproject without importing the
datasets app's CRSService directly (keeps app boundaries clean)."""
def reproject_wkt(shapely_geom, source_crs: str, target_crs: str):
    from pyproj import Transformer
    from shapely.ops import transform as shp_transform
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return shp_transform(transformer.transform, shapely_geom)
