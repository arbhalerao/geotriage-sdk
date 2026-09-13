from typing import Any

import numpy as np

from geotriage.bands import Bands, Raster
from geotriage import Model, Requires, Score, Thresholds

# physically plausible surface reflectance
# values outside this are sensor artefacts
_REFLECTANCE_RANGE = (-0.5, 1.5)
_WATER_NDWI_THRESHOLD = 0.3
_MIN_VALID_PIXELS = 10


class NDWIWaterDetector(Model):
    slug = "ndwi-water-detector"
    name = "NDWI Water Body Detector"
    description = "Computes the Normalized Difference Water Index " "(NDWI = (Green − NIR) / (Green + NIR)) to detect surface water extent " "and flag changes relative to configured thresholds."

    requires = Requires(bands=["green", "nir"], max_cloud_cover=30.0)

    scores = {
        "ndwi_mean": Score(
            description="Mean NDWI across all valid pixels in the AOI",
            unit="index",
            range=(-1.0, 1.0),
            primary=True,
            thresholds=Thresholds(green=(0.3, 1.0), yellow=(0.0, 0.3)),
        ),
        "water_fraction": Score(
            description="Fraction of valid pixels classified as water (NDWI > 0.3)",
            unit="fraction",
            range=(0.0, 1.0),
            thresholds=Thresholds(green=(0.5, 1.0), yellow=(0.2, 0.5)),
        ),
    }

    rasters = ["ndwi"]

    def _ndwi(self, bands: Bands) -> Raster:
        green = bands.green.mask_outside(*_REFLECTANCE_RANGE)
        nir = bands.nir.mask_outside(*_REFLECTANCE_RANGE)

        denominator = green + nir
        with np.errstate(divide="ignore", invalid="ignore"):
            ndwi = (green - nir) / denominator
        return ndwi.mask_where(np.abs(np.asarray(denominator)) <= 1e-10)

    def run(self, bands: Bands) -> dict[str, Any]:
        ndwi = self._ndwi(bands)
        n_valid = ndwi.valid_count

        if n_valid < _MIN_VALID_PIXELS:
            return {"ndwi_mean": None, "water_fraction": None, "valid_pixel_count": n_valid}

        return {
            "ndwi_mean": round(ndwi.nanmean(), 6),
            "water_fraction": round(ndwi.fraction_above(_WATER_NDWI_THRESHOLD), 6),
            "valid_pixel_count": n_valid,
        }

    def derived_rasters(self, bands: Bands) -> dict[str, Any]:
        return {"ndwi": self._ndwi(bands)}
