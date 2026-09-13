import json

import pytest

from geotriage import check_descriptor, describe
from geotriage.descriptor import DESCRIPTOR_VERSION, collection_from_descriptor


def round_trip(obj):
    return json.loads(json.dumps(describe(obj)))


def test_a_model_descriptor_survives_json(model):
    assert check_descriptor(round_trip(model)) == []


def test_a_provider_descriptor_survives_json(provider):
    assert check_descriptor(round_trip(provider)) == []


def test_a_model_descriptor_carries_the_declarations(model):
    d = round_trip(model)
    assert d["kind"] == "model"
    assert d["slug"] == model.slug
    assert d["requires"]["bands"] == ["thermal1"]
    assert d["requires"]["max_cloud_cover"] == 20.0
    assert d["scores"]["mean_c"]["primary"] is True
    assert d["scores"]["mean_c"]["thresholds"]["green"] == [-20.0, 30.0]
    assert d["rasters"] == ["temperature"]
    assert d["prefilter"] is None


def test_a_prefilter_crosses_the_boundary(screened_model):
    d = round_trip(screened_model)
    assert d["prefilter"] == {"bands": ["thermal1"], "gsd_m": 300.0}


def test_a_provider_descriptor_carries_its_band_table(provider):
    d = round_trip(provider)
    assert d["kind"] == "provider"
    assert d["auth"] == "NoAuth"
    bands = d["collections"]["optical-thermal"]["bands"]
    assert {b["normalized_name"]: b["asset_key"] for b in bands} == {"green": "B03", "thermal1": "lwir11"}


def test_a_collection_rebuilds_from_its_descriptor(provider, collection):
    rebuilt = collection_from_descriptor(round_trip(provider)["collections"]["optical-thermal"])
    assert rebuilt.slug == collection.slug
    assert rebuilt.resolution_m == collection.resolution_m
    assert rebuilt.band("thermal1").scale == collection.band("thermal1").scale
    assert rebuilt.band("thermal1").offset == collection.band("thermal1").offset


def test_describing_something_that_is_neither_is_an_error():
    with pytest.raises(TypeError):
        describe(object())


def test_a_descriptor_from_a_newer_platform_is_refused(model):
    d = round_trip(model)
    d["descriptor_version"] = DESCRIPTOR_VERSION + 1
    problems = check_descriptor(d)
    assert any("descriptor_version" in p for p in problems), problems


def test_a_descriptor_that_is_not_an_object_is_refused():
    assert check_descriptor([1, 2, 3])


def test_an_unknown_kind_is_refused(model):
    d = round_trip(model)
    d["kind"] = "something-else"
    assert any("kind" in p for p in check_descriptor(d))


def test_the_descriptor_checks_match_the_live_checks(model):
    """a model that is incoherent as an object stays incoherent as JSON"""
    d = round_trip(model)
    d["scores"]["hot_fraction"]["primary"] = True
    assert any("primary" in p for p in check_descriptor(d))
