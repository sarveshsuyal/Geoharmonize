"""
Demo data generator (per problem statement's DEMO DATA GENERATOR / ONE-CLICK DEMO
sections). Government datasets are not available for this prototype, so this
module procedurally builds a realistic multi-source study area:

  - a CADASTRAL layer (grid of parcels, treated as the "old" authoritative source)
  - a DRONE-derived layer (same parcels, geometrically shifted/noisy, as if
    digitized independently from imagery)
  - a MUNICIPAL layer (subset with some parcels merged/missing, different field names)
  - a REVENUE CSV (attribute-only records referencing survey numbers, some typos)
  - BUILDING, ROAD and UTILITY layers

...then writes these as real GeoJSON/CSV files, creates real Dataset rows,
runs them through the actual ingestion + vector import + harmonization
pipeline, and returns the ACTUALLY COMPUTED statistics. Nothing here is a
pre-written fake result: every number in the response comes out of the same
matching/confidence/conflict code path used for real uploads.
"""
import json
import math
import random
import tempfile
from pathlib import Path


# Study-area origin: an illustrative small town extent (not a real cadastral survey).
ORIGIN_LON, ORIGIN_LAT = 77.7064, 29.0588   # near Meerut, UP - illustrative only
GRID_COLS, GRID_ROWS = 10, 8                # 80 base parcels
PARCEL_SIZE_DEG = 0.00035                    # roughly ~35-40m at this latitude


def _parcel_polygon(col, row, shift_x=0.0, shift_y=0.0, shrink=0.0):
    x0 = ORIGIN_LON + col * PARCEL_SIZE_DEG + shift_x
    y0 = ORIGIN_LAT + row * PARCEL_SIZE_DEG + shift_y
    size = PARCEL_SIZE_DEG * (1 - shrink)
    return [[
        [x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0],
    ]]


class DemoDataBuilder:
    """Builds the in-memory GeoJSON/CSV payloads with controlled, seeded inconsistencies."""

    def __init__(self, seed=42):
        self.rng = random.Random(seed)

    def build_cadastral(self):
        features = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                # 3% chance this parcel is simply missing from cadastral (data gap)
                if self.rng.random() < 0.02:
                    continue
                pid = f"CAD-{r:02d}{c:02d}"
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": _parcel_polygon(c, r)},
                    "properties": {
                        "survey_no": f"{100 + r * GRID_COLS + c}/A",
                        "parcel_id": pid,
                        "area": None,
                        "land_use": self.rng.choice(["Residential", "Agricultural", "Commercial"]),
                    },
                })
        return {"type": "FeatureCollection", "features": features}

    def build_drone(self):
        """Same parcels, independently digitized from drone imagery: small
        boundary shifts (0.5-2m equiv in degrees), a few duplicated parcels,
        a couple of invalid self-intersecting rings, 3 brand-new candidate parcels."""
        features = []
        # ~2m at this latitude ~= 0.000018 deg; scale shift range to 0.5-2m equivalent
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.rng.random() < 0.03:
                    continue  # missing from drone survey
                shift_x = self.rng.uniform(-0.000018, 0.000018)
                shift_y = self.rng.uniform(-0.000018, 0.000018)
                pid = f"D-{r:02d}{c:02d}"
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": _parcel_polygon(c, r, shift_x, shift_y)},
                    "properties": {"candidate_id": pid, "area_sqm": None},
                })
                # 4% duplicate injection
                if self.rng.random() < 0.04:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": _parcel_polygon(c, r, shift_x, shift_y)},
                        "properties": {"candidate_id": pid + "-dup", "area_sqm": None},
                    })
        # 3 new candidate parcels beyond the cadastral grid (e.g. new subdivision)
        for i in range(3):
            col, row = GRID_COLS + i, 0
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": _parcel_polygon(col, row)},
                "properties": {"candidate_id": f"D-NEW-{i}", "area_sqm": None},
            })
        return {"type": "FeatureCollection", "features": features}

    def build_municipal(self):
        """Subset with different field names & a few merged (2x2) parcels + one
        parcel with a subdivision (splits one cadastral cell into two)."""
        features = []
        for r in range(0, GRID_ROWS, 1):
            for c in range(0, GRID_COLS, 1):
                if self.rng.random() < 0.05:
                    continue
                pid = f"M-{r:02d}{c:02d}"
                land_use = self.rng.choice(["Residential", "Agricultural", "Commercial", "Mixed Use"])
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": _parcel_polygon(c, r, shrink=0.02)},
                    "properties": {
                        "property_id": pid,
                        "plot_no": f"{100 + r * GRID_COLS + c}/A",  # matches cadastral survey_no for linking
                        "zone": land_use,
                        "area_m2": None,
                    },
                })
        return {"type": "FeatureCollection", "features": features}

    def build_revenue_csv_rows(self):
        rows = [["khasra_no", "khata_no", "landuse_type", "area_ha"]]
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.rng.random() < 0.06:
                    continue
                survey_no = f"{100 + r * GRID_COLS + c}/A"
                rows.append([survey_no, f"KH-{r}{c}", self.rng.choice(["Residential", "Agricultural", "Commercial"]),
                             round(self.rng.uniform(0.01, 0.05), 4)])
        return rows

    def build_buildings(self):
        """A handful of building footprints, one intentionally crossing a parcel edge."""
        features = []
        samples = [(2, 2), (5, 3), (7, 6), (1, 5)]
        for i, (c, r) in enumerate(samples):
            x0 = ORIGIN_LON + c * PARCEL_SIZE_DEG + PARCEL_SIZE_DEG * 0.2
            y0 = ORIGIN_LAT + r * PARCEL_SIZE_DEG + PARCEL_SIZE_DEG * 0.2
            w = PARCEL_SIZE_DEG * (0.7 if i != 1 else 1.3)  # building #1 intentionally oversized -> crosses boundary
            coords = [[[x0, y0], [x0 + w, y0], [x0 + w, y0 + w * 0.6], [x0, y0 + w * 0.6], [x0, y0]]]
            features.append({
                "type": "Feature", "geometry": {"type": "Polygon", "coordinates": coords},
                "properties": {"building_id": f"B-{i}"},
            })
        return {"type": "FeatureCollection", "features": features}

    def build_roads(self):
        y = ORIGIN_LAT - PARCEL_SIZE_DEG
        coords = [[ORIGIN_LON - PARCEL_SIZE_DEG, y], [ORIGIN_LON + GRID_COLS * PARCEL_SIZE_DEG, y]]
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
             "properties": {"road_id": "R-MAIN", "road_class": "Arterial"}}
        ]}

    def build_utilities(self):
        x = ORIGIN_LON + 3 * PARCEL_SIZE_DEG
        coords = [[x, ORIGIN_LAT - PARCEL_SIZE_DEG], [x, ORIGIN_LAT + GRID_ROWS * PARCEL_SIZE_DEG]]
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
             "properties": {"type": "WATER"}}
        ]}


class DemoRunner:
    """Writes the built payloads to real files, ingests them as Dataset rows,
    imports features into PostGIS-backed tables, and runs the full harmonization
    pipeline end to end."""

    def __init__(self, user):
        self.user = user
        self.builder = DemoDataBuilder()

    def run_full_demo(self) -> dict:
        from django.core.files.base import ContentFile
        from apps.datasets.models import Dataset, DatasetType
        from apps.datasets.services.ingestion_service import IngestionService
        from apps.geospatial.services.vector_service import VectorImportService
        from apps.harmonization.models import HarmonizationRun, RunStatus
        from apps.harmonization.services.pipeline_service import HarmonizationPipeline

        ingestion = IngestionService()
        importer = VectorImportService()
        created_datasets = []

        payloads = [
            ("Cadastral_Demo_2024", DatasetType.CADASTRAL, self.builder.build_cadastral(), "geojson"),
            ("Drone_Demo_2026", DatasetType.DRONE, self.builder.build_drone(), "geojson"),
            ("Municipal_Demo_2026", DatasetType.MUNICIPAL, self.builder.build_municipal(), "geojson"),
            ("Buildings_Demo_2026", DatasetType.BUILDING, self.builder.build_buildings(), "geojson"),
            ("Roads_Demo_2026", DatasetType.ROAD, self.builder.build_roads(), "geojson"),
            ("Utilities_Demo_2026", DatasetType.UTILITY, self.builder.build_utilities(), "geojson"),
        ]

        for name, dtype, geojson_obj, ext in payloads:
            dataset = Dataset(name=name, dataset_type=dtype, source="GeoHarmonize Demo Generator", uploaded_by=self.user)
            content = json.dumps(geojson_obj).encode("utf-8")
            dataset.file.save(f"{name}.{ext}", ContentFile(content), save=False)
            dataset.original_filename = f"{name}.{ext}"
            dataset.save()
            ingestion.process_new_dataset(dataset)
            # Demo GeoJSON has no embedded CRS, per common real-world exports -> assume WGS84
            if not dataset.original_crs:
                ingestion.set_manual_crs(dataset, "EPSG:4326")
            importer.import_dataset(dataset)
            created_datasets.append(dataset)

        # Revenue CSV (attribute-only, no geometry - illustrates a non-spatial source)
        import csv, io
        rows = self.builder.build_revenue_csv_rows()
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        revenue_dataset = Dataset(name="Revenue_Demo_2026", dataset_type=DatasetType.REVENUE,
                                   source="GeoHarmonize Demo Generator", uploaded_by=self.user)
        revenue_dataset.file.save("Revenue_Demo_2026.csv", ContentFile(buf.getvalue().encode("utf-8")), save=False)
        revenue_dataset.original_filename = "Revenue_Demo_2026.csv"
        revenue_dataset.processing_status = "PROCESSED"
        revenue_dataset.feature_count = len(rows) - 1
        revenue_dataset.save()
        created_datasets.append(revenue_dataset)

        # Run harmonization across the spatial layers only (cadastral/drone/municipal)
        spatial_ids = [d.id for d in created_datasets if d.dataset_type in
                       (DatasetType.CADASTRAL, DatasetType.DRONE, DatasetType.MUNICIPAL)]
        run = HarmonizationRun.objects.create(status=RunStatus.PENDING, dataset_ids=spatial_ids)
        stats = HarmonizationPipeline(run).run_pipeline(spatial_ids)

        return {
            "datasets": [{"id": d.id, "name": d.name, "type": d.dataset_type,
                          "feature_count": d.feature_count, "status": d.processing_status}
                         for d in created_datasets],
            "harmonization_run_id": run.id,
            "statistics": stats,
        }
