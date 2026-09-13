from apps.harmonization.services.attribute_mapping import map_to_canonical_attributes_offline


def test_maps_known_cadastral_fields():
    raw = {"survey_no": "101/A", "khasra_no": "999", "area_sqm": 250.0, "unknown_field": "x"}
    canonical = map_to_canonical_attributes_offline(raw, "CADASTRAL")
    assert canonical["survey_number"] in ("101/A", "999")  # last-writer-wins on aliasing to same canonical field
    assert canonical["area"] == 250.0
    assert "unknown_field" in canonical["_unmapped_fields"]


def test_leaves_unrecognized_dataset_type_fully_unmapped():
    raw = {"foo": "bar"}
    canonical = map_to_canonical_attributes_offline(raw, "SATELLITE")
    assert canonical["_unmapped_fields"] == {"foo": "bar"}
