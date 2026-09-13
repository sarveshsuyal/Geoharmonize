import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.gis.geos import GEOSGeometry

from apps.datasets.models import Dataset, GeometryKind, ProcessingStatus
from apps.harmonization.models import HarmonizationRun, MatchStatus, ParcelMatch, ParcelMatchReviewAction
from apps.harmonization.serializers import StartHarmonizationSerializer
from apps.harmonization.services.export_service import HarmonizedExportService
from apps.parcels.models import Parcel


def geojson_file(name, shift=0):
    return SimpleUploadedFile(
        name,
        json.dumps({
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [{
                "type": "Feature",
                "properties": {"parcel_id": "P-1", "survey_no": "S-1"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77 + shift, 28], [77.01 + shift, 28], [77.01 + shift, 28.01], [77 + shift, 28]]],
                },
            }],
        }).encode(),
        content_type="application/geo+json",
    )


def make_dataset(name, user):
    return Dataset.objects.create(
        name=name,
        dataset_type="CADASTRAL",
        source="test",
        file=SimpleUploadedFile(f"{name}.geojson", b"{}", content_type="application/json"),
        original_crs="EPSG:4326",
        target_crs="EPSG:32644",
        geometry_type=GeometryKind.POLYGON,
        processing_status=ProcessingStatus.VALIDATED,
        uploaded_by=user,
    )


@pytest.mark.django_db
def test_start_serializer_rejects_missing_and_unready_datasets(admin_user):
    ready = make_dataset("ready", admin_user)
    missing = StartHarmonizationSerializer(data={"dataset_ids": [ready.id, 999999]})
    assert not missing.is_valid()
    assert "not found" in str(missing.errors).lower()

    unready = make_dataset("unready", admin_user)
    unready.processing_status = ProcessingStatus.FAILED
    unready.save(update_fields=["processing_status"])
    invalid = StartHarmonizationSerializer(data={"dataset_ids": [ready.id, unready.id]})
    assert not invalid.is_valid()
    assert "validated" in str(invalid.errors).lower()


@pytest.mark.django_db
def test_export_excludes_rejected_match_and_keeps_real_geometry(admin_user):
    source_dataset = make_dataset("source", admin_user)
    target_dataset = make_dataset("target", admin_user)
    geometry = GEOSGeometry(json.dumps({
        "type": "MultiPolygon",
        "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]],
    }), srid=4326)
    source = Parcel.objects.create(parcel_id="SRC-1", geometry=geometry, area=1)
    target = Parcel.objects.create(parcel_id="TGT-1", geometry=geometry, area=1)
    source.source_datasets.add(source_dataset)
    target.source_datasets.add(target_dataset)
    run = HarmonizationRun.objects.create(dataset_ids=[source_dataset.id, target_dataset.id])
    rejected = ParcelMatch.objects.create(
        run=run, source_parcel=source, target_parcel=target,
        overlap_ratio=1, area_similarity=1, centroid_distance_m=0,
        shape_similarity=1, boundary_similarity=1, attribute_similarity=1,
        overall_confidence=100, status=MatchStatus.REJECTED,
    )

    output = HarmonizedExportService().generate_harmonized_geojson(run)

    assert output["metadata"]["matched_count"] == 0
    assert all(feature["properties"].get("match_id") != rejected.id for feature in output["features"])
    assert HarmonizedExportService().verify_geojson(output)


@pytest.mark.django_db
def test_match_review_is_immutable_and_rejection_unharmonizes(admin_user):
    source_dataset = make_dataset("source-review", admin_user)
    target_dataset = make_dataset("target-review", admin_user)
    geometry = GEOSGeometry("MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)))", srid=4326)
    source = Parcel.objects.create(parcel_id="SRC-R", geometry=geometry, is_harmonized=True)
    target = Parcel.objects.create(parcel_id="TGT-R", geometry=geometry)
    source.source_datasets.add(source_dataset)
    target.source_datasets.add(target_dataset)
    source.harmonized_from.add(target)
    run = HarmonizationRun.objects.create(dataset_ids=[source_dataset.id, target_dataset.id])
    match = ParcelMatch.objects.create(
        run=run, source_parcel=source, target_parcel=target,
        overlap_ratio=1, area_similarity=1, centroid_distance_m=0,
        shape_similarity=1, boundary_similarity=1, attribute_similarity=1,
        overall_confidence=100, status=MatchStatus.MATCH,
    )

    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=admin_user)
    response = client.post(f"/api/harmonization/matches/{match.id}/review/", {"action": "REJECT", "notes": "Boundary differs"}, format="json")

    source.refresh_from_db()
    assert response.status_code == 200
    assert source.is_harmonized is False
    assert ParcelMatchReviewAction.objects.filter(match=match, action="REJECT").count() == 1


@pytest.mark.django_db
def test_real_upload_process_harmonize_and_export(client, admin_user):
    client.force_login(admin_user)
    upload_url = "/api/datasets/"
    payload = {"name": "API source", "dataset_type": "CADASTRAL", "source": "test", "file": geojson_file("source.geojson")}
    source_response = client.post(upload_url, payload, format="multipart")
    target_response = client.post(
        upload_url,
        {"name": "API target", "dataset_type": "CADASTRAL", "source": "test", "file": geojson_file("target.geojson", 0.00001)},
        format="multipart",
    )
    assert source_response.status_code == 201
    assert target_response.status_code == 201
    source_id = source_response.json()["id"]
    target_id = target_response.json()["id"]
    assert source_response.json()["feature_count"] == 1
    assert source_response.json()["original_crs"] == "EPSG:4326"

    assert client.post(f"{upload_url}{source_id}/process/").status_code == 200
    assert client.post(f"{upload_url}{target_id}/process/").status_code == 200
    run_response = client.post("/api/harmonization/run/", {"dataset_ids": [source_id, target_id]}, format="json")

    assert run_response.status_code == 201
    run_id = run_response.json()["id"]
    assert run_response.json()["status"] == "COMPLETED"
    export_response = client.get(f"/api/harmonization/runs/{run_id}/export/")
    exported = json.loads(export_response.content)
    assert export_response.status_code == 200
    assert exported["type"] == "FeatureCollection"
    assert HarmonizedExportService().verify_geojson(exported)


@pytest.mark.django_db
def test_pipeline_matching_uses_projected_comparison_crs(admin_user):
    source_dataset = make_dataset("projected-source", admin_user)
    target_dataset = make_dataset("projected-target", admin_user)
    geometry = GEOSGeometry("MULTIPOLYGON (((77 28, 77.001 28, 77.001 28.001, 77 28)))", srid=4326)
    source = Parcel.objects.create(parcel_id="SRC-P", geometry=geometry, area=1)
    target = Parcel.objects.create(parcel_id="TGT-P", geometry=geometry, area=1)
    source.source_datasets.add(source_dataset)
    target.source_datasets.add(target_dataset)
    run = HarmonizationRun.objects.create(dataset_ids=[source_dataset.id, target_dataset.id])

    from apps.harmonization.services.pipeline_service import HarmonizationPipeline
    pipeline = HarmonizationPipeline(run)
    result = pipeline._run_matching([source_dataset, target_dataset])

    assert result["matches"]
    assert result["matches"][0]["metrics"].centroid_distance_m == 0
    assert pipeline.comparison_crs == "EPSG:32643"