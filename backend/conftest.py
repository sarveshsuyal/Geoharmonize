import pytest


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_user(username="admin", password="pass1234", role="ADMIN")


@pytest.fixture
def gis_officer(django_user_model):
    return django_user_model.objects.create_user(username="officer", password="pass1234", role="GIS_OFFICER")


@pytest.fixture
def viewer_user(django_user_model):
    return django_user_model.objects.create_user(username="viewer", password="pass1234", role="VIEWER")
