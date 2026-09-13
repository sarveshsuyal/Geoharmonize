import pytest
from apps.datasets.services.ingestion_service import IngestionService, IngestionError


def test_validate_extension_accepts_known_formats():
    svc = IngestionService()
    for name in ["parcels.geojson", "survey.zip", "ortho.tif", "boundary.kml", "records.csv"]:
        assert svc.validate_extension(name)


def test_validate_extension_rejects_unknown_format():
    svc = IngestionService()
    with pytest.raises(IngestionError) as exc_info:
        svc.validate_extension("document.docx")
    assert exc_info.value.code == "UNSUPPORTED_FORMAT"


def test_validate_size_rejects_oversized_file(settings):
    settings.GEOHARMONIZE["MAX_UPLOAD_SIZE_MB"] = 1
    svc = IngestionService()
    with pytest.raises(IngestionError) as exc_info:
        svc.validate_size(2 * 1024 * 1024)
    assert exc_info.value.code == "FILE_TOO_LARGE"


@pytest.mark.django_db
def test_dataset_needs_crs_flow(admin_user):
    from apps.datasets.models import Dataset, DatasetType, ProcessingStatus
    from django.core.files.base import ContentFile

    dataset = Dataset(name="No CRS Layer", dataset_type=DatasetType.CADASTRAL,
                       source="test", uploaded_by=admin_user)
    dataset.file.save("no_crs.geojson", ContentFile(b'{"type":"FeatureCollection","features":[]}'), save=False)
    dataset.processing_status = ProcessingStatus.NEEDS_CRS
    dataset.save()

    svc = IngestionService()
    updated = svc.set_manual_crs(dataset, "EPSG:32644")
    assert updated.original_crs == "EPSG:32644"
    assert updated.crs_confidence == "USER_SPECIFIED"
    assert updated.processing_status == ProcessingStatus.VALIDATED
