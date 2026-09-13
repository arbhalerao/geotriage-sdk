from typing import Any

from geotriage.bands import Bands, Raster
from geotriage import Model, Requires, Score, Thresholds

_KELVIN_TO_C = 273.15
_HOT_THRESHOLD_C = 35.0
# physically plausible land surface temperature
# outside this is a sensor artefact
_PLAUSIBLE_C = (-80.0, 100.0)
_MIN_VALID = 10


class LSTDetector(Model):
    slug = "lst-detector"
    name = "Land Surface Temperature Detector"
    description = (
        "Derives land surface temperature (LST) from Landsat thermal infrared imagery "
        "(Band 10 / LWIR11). Reports mean surface temperature and the fraction of pixels "
        "exceeding a configurable heat threshold."
    )

    requires = Requires(bands=["thermal1"], max_cloud_cover=20.0)

    scores = {
        "lst_mean": Score(
            description="Mean land surface temperature across valid pixels",
            unit="°C",
            range=(-20.0, 70.0),
            primary=True,
            thresholds=Thresholds(green=(-20.0, 30.0), yellow=(30.0, 40.0)),
        ),
        "hot_fraction": Score(
            description=f"Fraction of valid pixels above {_HOT_THRESHOLD_C}°C",
            unit="fraction",
            range=(0.0, 1.0),
            thresholds=Thresholds(green=(0.0, 0.1), yellow=(0.1, 0.3)),
        ),
    }

    rasters = ["lst"]

    def _lst(self, bands: Bands) -> Raster:
        # thermal1 arrives calibrated to Kelvin; the collection owns that conversion
        return (bands.thermal1 - _KELVIN_TO_C).mask_outside(*_PLAUSIBLE_C)

    def run(self, bands: Bands) -> dict[str, Any]:
        temp_c = self._lst(bands)
        n_valid = temp_c.valid_count

        if n_valid < _MIN_VALID:
            return {"lst_mean": None, "hot_fraction": None, "valid_pixel_count": n_valid}

        return {
            "lst_mean": round(temp_c.nanmean(), 4),
            "hot_fraction": round(temp_c.fraction_above(_HOT_THRESHOLD_C), 6),
            "valid_pixel_count": n_valid,
        }

    def derived_rasters(self, bands: Bands) -> dict[str, Any]:
        return {"lst": self._lst(bands)}
