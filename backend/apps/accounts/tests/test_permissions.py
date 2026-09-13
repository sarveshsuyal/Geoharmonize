import pytest
from apps.accounts.models import Role


@pytest.mark.django_db
def test_role_permission_helpers(admin_user, gis_officer, viewer_user):
    assert admin_user.can_upload and admin_user.can_process and admin_user.can_edit_geometry
    assert gis_officer.can_upload and gis_officer.can_process
    assert viewer_user.is_read_only
    assert not viewer_user.can_upload
    assert not viewer_user.can_edit_geometry


@pytest.mark.django_db
def test_login_endpoint(client, gis_officer):
    resp = client.post("/api/auth/login/", {"username": "officer", "password": "pass1234"}, content_type="application/json")
    assert resp.status_code == 200
    assert "access" in resp.json()
    assert resp.json()["user"]["role"] == "GIS_OFFICER"


@pytest.mark.django_db
def test_login_rejects_bad_credentials(client, gis_officer):
    resp = client.post("/api/auth/login/", {"username": "officer", "password": "wrong"}, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_rejects_unknown_username(client):
    resp = client.post("/api/auth/login/", {"username": "missing", "password": "pass1234"}, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_rejects_inactive_user(client, django_user_model):
    django_user_model.objects.create_user(username="inactive", password="pass1234", is_active=False)
    resp = client.post("/api/auth/login/", {"username": "inactive", "password": "pass1234"}, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_allows_expected_development_admin(client, django_user_model):
    user = django_user_model.objects.create_user(username="sarvesh", password="sarvesh@suyal", role="ADMIN")
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])

    resp = client.post("/api/auth/login/", {"username": "sarvesh", "password": "sarvesh@suyal"}, content_type="application/json")

    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "sarvesh"
    assert resp.json()["user"]["role"] == "ADMIN"
