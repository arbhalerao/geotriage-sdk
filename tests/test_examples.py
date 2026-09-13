import importlib.util
import pathlib

import pytest

from geotriage import check_model, check_provider, split_output
from geotriage.bands import Bands

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


def load(relative: str, name: str):
    path = EXAMPLES / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)()


@pytest.mark.parametrize(
    "relative,name",
    [
        ("models/ndwi_water.py", "NDWIWaterDetector"),
        ("models/lst.py", "LSTDetector"),
        ("models/ndvi_vegetation.py", "NDVIVegetationDetector"),
    ],
)
def test_example_models_are_conformant(relative, name):
    assert check_model(load(relative, name)) == []


@pytest.mark.parametrize(
    "relative,name",
    [
        ("providers/earth_search.py", "EarthSearchProvider"),
        ("providers/planetary_computer_provider.py", "PlanetaryComputerProvider"),
    ],
)
def test_example_providers_are_conformant(relative, name):
    assert check_provider(load(relative, name)) == []


def test_example_models_score_a_synthetic_scene():
    import numpy as np

    model = load("models/ndwi_water.py", "NDWIWaterDetector")
    rng = np.random.default_rng(0)
    bands = Bands({name: rng.uniform(0.02, 0.6, size=(16, 16)) for name in model.requires.bands}, collection_slug="x")
    scores, _ = split_output(model, model.run(bands))
    assert scores["ndwi_mean"] is not None


def staged(collection, raw):
    """reproduce what the platform hands a model: calibrated, AOI-clipped bands"""
    return Bands(
        {name: collection.band(name).calibrate(arr) for name, arr in raw.items()},
        collection_slug=collection.slug,
    )


def raw_scene(seed: int, shape=(64, 64)):
    """PCG64 is stable across numpy releases, so the values these tests lock are reproducible"""
    import numpy as np

    arr = np.random.default_rng(seed).uniform(5000, 30000, size=shape).astype(np.float32)
    arr[:5, :5] = np.nan
    return arr


def collection_of(relative: str, name: str, slug: str):
    return load(relative, name).collections[slug]


def test_ndwi_on_landsat_surface_reflectance():
    landsat = collection_of("providers/planetary_computer_provider.py", "PlanetaryComputerProvider", "landsat-c2-l2")
    bands = staged(landsat, {"green": raw_scene(1), "nir": raw_scene(2)})
    out = load("models/ndwi_water.py", "NDWIWaterDetector").run(bands)
    assert out["ndwi_mean"] == pytest.approx(-0.033014)
    assert out["water_fraction"] == pytest.approx(0.309015)
    assert out["valid_pixel_count"] == 4071


def test_ndwi_on_sentinel2():
    s2 = collection_of("providers/earth_search.py", "EarthSearchProvider", "sentinel-2-l2a")
    bands = staged(s2, {"green": raw_scene(7), "nir": raw_scene(8)})
    out = load("models/ndwi_water.py", "NDWIWaterDetector").run(bands)
    assert out["ndwi_mean"] == pytest.approx(0.002147)
    assert out["water_fraction"] == pytest.approx(0.078947)
    assert out["valid_pixel_count"] == 646


def test_lst_on_landsat_thermal():
    landsat = collection_of("providers/planetary_computer_provider.py", "PlanetaryComputerProvider", "landsat-c2-l2")
    bands = staged(landsat, {"thermal1": raw_scene(3)})
    out = load("models/lst.py", "LSTDetector").run(bands)
    assert out["lst_mean"] == pytest.approx(-50.4494)
    assert out["hot_fraction"] == pytest.approx(0.0)
    assert out["valid_pixel_count"] == 2747


def test_derived_raster_matches_the_scored_array():
    landsat = collection_of("providers/planetary_computer_provider.py", "PlanetaryComputerProvider", "landsat-c2-l2")
    bands = staged(landsat, {"green": raw_scene(1), "nir": raw_scene(2)})
    model = load("models/ndwi_water.py", "NDWIWaterDetector")
    raster = model.derived_rasters(bands)["ndwi"]
    assert raster.valid_count == model.run(bands)["valid_pixel_count"]


def test_a_model_reads_the_same_band_name_across_archives():
    model = load("models/ndwi_water.py", "NDWIWaterDetector")
    landsat = collection_of("providers/planetary_computer_provider.py", "PlanetaryComputerProvider", "landsat-c2-l2")
    s2 = collection_of("providers/earth_search.py", "EarthSearchProvider", "sentinel-2-l2a")
    for collection in (landsat, s2):
        out = model.run(staged(collection, {"green": raw_scene(11), "nir": raw_scene(12)}))
        assert out["ndwi_mean"] is not None
