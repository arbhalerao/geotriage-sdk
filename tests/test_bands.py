import numpy as np
import pytest

from geotriage.bands import Bands, Raster


def test_raster_arithmetic_stays_a_raster():
    a, b = Raster([[1.0, 2.0]]), Raster([[1.0, 1.0]])
    assert isinstance((a - b) / (a + b), Raster)


def test_raster_reductions_ignore_nodata():
    r = Raster([[1.0, 3.0, np.nan]])
    assert r.valid_count == 2
    assert r.nanmean() == pytest.approx(2.0)
    assert r.nanmedian() == pytest.approx(2.0)
    assert r.nanmin() == pytest.approx(1.0)
    assert r.nanmax() == pytest.approx(3.0)
    assert r.fraction_above(2.0) == pytest.approx(0.5)
    assert r.fraction_below(2.0) == pytest.approx(0.5)


def test_raster_reductions_on_empty_are_none():
    r = Raster([[np.nan, np.nan]])
    assert r.valid_count == 0
    assert r.nanmean() is None
    assert r.nanstd() is None
    assert r.fraction_above(0.0) is None


def test_mask_outside_marks_implausible_values_nodata():
    r = Raster([[-2.0, 0.5, 9.0]]).mask_outside(-0.5, 1.5)
    assert r.valid_count == 1
    assert r.nanmean() == pytest.approx(0.5)


def test_mask_where_marks_the_selected_pixels_nodata():
    r = Raster([[1.0, 2.0, 3.0]])
    masked = r.mask_where(np.asarray(r) > 2.0)
    assert masked.valid_count == 2
    assert r.valid_count == 3, "masking must not mutate the original"


def test_bands_accessible_by_attribute_and_item():
    bands = Bands({"green": [[1.0]]}, collection_slug="x")
    assert isinstance(bands.green, Raster)
    assert bands["green"] == bands.green


def test_missing_band_names_what_is_available():
    bands = Bands({"green": [[1.0]], "nir": [[2.0]]}, collection_slug="x")
    with pytest.raises(AttributeError) as exc:
        bands.swir1
    message = str(exc.value)
    assert "swir1" in message and "green, nir" in message and "Requires" in message


def test_bands_report_their_shape_and_membership():
    bands = Bands({"green": [[1.0, 2.0]], "nir": [[3.0, 4.0]]}, collection_slug="x")
    assert bands.shape == (1, 2)
    assert bands.names == ["green", "nir"]
    assert "green" in bands and "swir1" not in bands
    assert len(bands) == 2
    assert sorted(bands) == ["green", "nir"]


def test_stack_returns_band_major_array():
    bands = Bands({"r": [[1.0, 1.0]], "g": [[2.0, 2.0]]}, collection_slug="x")
    assert bands.stack("r", "g").shape == (2, 1, 2)


def test_stack_without_names_is_rejected():
    bands = Bands({"r": [[1.0]]}, collection_slug="x")
    with pytest.raises(ValueError):
        bands.stack()
