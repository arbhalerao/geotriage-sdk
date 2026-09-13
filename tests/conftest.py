import pytest

from geotriage import Band, Collection, Model, Prefilter, Provider, Requires, Score, Thresholds


class Thermal(Model):
    slug = "thermal"
    name = "Thermal Detector"
    requires = Requires(bands=["thermal1"], max_cloud_cover=20.0)
    scores = {
        "mean_c": Score(primary=True, unit="°C", thresholds=Thresholds(green=(-20.0, 30.0), yellow=(30.0, 40.0))),
        "hot_fraction": Score(unit="fraction", thresholds=Thresholds(green=(0.0, 0.1), yellow=(0.1, 0.3))),
    }
    rasters = ["temperature"]

    def run(self, bands):
        temp = bands.thermal1 - 273.15
        return {"mean_c": temp.nanmean(), "hot_fraction": temp.fraction_above(35.0)}

    def derived_rasters(self, bands):
        return {"temperature": bands.thermal1 - 273.15}


class Screened(Thermal):
    slug = "screened"
    name = "Thermal Detector With A Gate"
    prefilter = Prefilter(bands=["thermal1"], gsd_m=300.0)

    def screen(self, bands):
        return bands.thermal1.valid_count > 0


class Archive(Provider):
    slug = "archive"
    name = "Test Archive"
    stac_api_url = "https://stac.example.com/v1"
    collections = {
        "optical-thermal": Collection(
            slug="optical-thermal",
            display_name="Optical And Thermal",
            processing_level="SR",
            resolution_m=30.0,
            cloud_cover_property="eo:cloud_cover",
            bands=[
                Band("green", "B03", scale=0.0001),
                Band("thermal1", "lwir11", scale=0.00341802, offset=149.0),
            ],
        )
    }


@pytest.fixture
def model():
    return Thermal()


@pytest.fixture
def screened_model():
    return Screened()


@pytest.fixture
def provider():
    return Archive()


@pytest.fixture
def collection(provider):
    return provider.collections["optical-thermal"]
