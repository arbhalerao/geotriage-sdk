import numpy as np
import pytest

from geotriage import Band, Collection, Provider, build_normalized_assets, check_collection, check_compatibility, check_provider


def test_band_calibrates_to_physical_units():
    band = Band("green", "B03", scale=0.0001, offset=0.0)
    raw = np.array([[0.0, 10000.0]], dtype=np.float32)
    np.testing.assert_allclose(band.calibrate(raw), [[0.0, 1.0]])


def test_calibration_is_identity_by_default():
    band = Band("green", "B03")
    raw = np.array([[1.0, 2.0]], dtype=np.float32)
    assert band.calibrate(raw) is raw


def test_calibration_preserves_nodata():
    band = Band("thermal1", "lwir11", scale=0.00341802, offset=149.0)
    raw = np.array([[np.nan, 30000.0]], dtype=np.float32)
    out = band.calibrate(raw)
    assert np.isnan(out[0, 0])
    assert out[0, 1] == pytest.approx(149.0 + 30000.0 * 0.00341802, rel=1e-6)


def test_thermal_and_optical_bands_calibrate_differently(collection):
    assert collection.band("thermal1").scale != collection.band("green").scale


def test_a_conformant_provider_has_no_problems(provider):
    assert check_provider(provider) == []


def test_provider_without_a_stac_url_is_rejected(provider):
    class NoUrl(Provider):
        slug, name, stac_api_url = "nourl", "No URL", ""
        collections = provider.collections

    assert any("stac_api_url" in p for p in check_provider(NoUrl()))


def test_collection_slug_must_match_its_key(provider):
    class Mismatched(Provider):
        slug, name = "mismatched", "Mismatched"
        stac_api_url = "https://stac.example.com/v1"
        collections = {"not-the-slug": provider.collections["optical-thermal"]}

    assert any("not-the-slug" in p for p in check_provider(Mismatched()))


def test_a_band_with_scale_zero_is_rejected():
    collection = Collection(
        slug="zeroed",
        display_name="Zeroed",
        resolution_m=10.0,
        bands=[Band("green", "B03", scale=0.0)],
    )
    problems = check_collection(collection)
    assert any("scale 0" in p for p in problems), problems


def test_a_collection_without_bands_is_rejected():
    collection = Collection(slug="empty", display_name="Empty", resolution_m=10.0)
    assert any("no bands" in p for p in check_collection(collection))


def test_a_duplicated_band_is_rejected():
    collection = Collection(
        slug="dup",
        display_name="Dup",
        resolution_m=10.0,
        bands=[Band("green", "B03"), Band("green", "B04")],
    )
    assert any("twice" in p for p in check_collection(collection))


def test_build_normalized_assets_maps_names_to_hrefs(collection):
    assets = {"B03": {"href": "https://example.com/green.tif"}}
    out = build_normalized_assets(assets, collection, ["green"])
    assert out == {"green": {"href": "https://example.com/green.tif", "asset_key": "B03"}}


def test_build_normalized_assets_names_the_missing_asset(collection):
    with pytest.raises(ValueError) as exc:
        build_normalized_assets({}, collection, ["green"])
    assert "B03" in str(exc.value)


def test_build_normalized_assets_rejects_a_band_the_collection_lacks(collection):
    with pytest.raises(ValueError) as exc:
        build_normalized_assets({}, collection, ["swir1"])
    assert "swir1" in str(exc.value)


def test_a_model_is_compatible_with_a_collection_carrying_its_bands(model, collection):
    assert check_compatibility(model, collection).level == "full"


def test_a_collection_lacking_a_required_band_is_incompatible(model):
    optical_only = Collection(
        slug="optical",
        display_name="Optical Only",
        resolution_m=10.0,
        cloud_cover_property="eo:cloud_cover",
        bands=[Band("green", "B03", scale=0.0001)],
    )
    result = check_compatibility(model, optical_only)
    assert result.level == "incompatible"
    assert not result.compatible
    assert result.reasons[0].code == "missing_bands"


def test_collection_without_cloud_cover_is_only_partially_compatible(model):
    no_cloud = Collection(
        slug="nocloud",
        display_name="No Cloud",
        resolution_m=10.0,
        cloud_cover_property=None,
        bands=[Band("thermal1", "lwir11")],
    )
    result = check_compatibility(model, no_cloud)
    assert result.level == "partial"
    assert result.compatible
    assert result.reasons[0].code == "no_cloud_cover"
