"""
NDVI vegetation detector

a worked example of what a customer's own detector looks like: written against the
contract, built into an image, and registered through the models page
"""

from geotriage import Bands, Model, Requires, Score, Thresholds

_VEGETATION_NDVI = 0.4
_MIN_VALID_PIXELS = 10
_REFLECTANCE_RANGE = (-0.5, 1.5)


class NDVIVegetationDetector(Model):
    slug = "ndvi-vegetation"
    name = "NDVI Vegetation Detector"
    description = "Normalized Difference Vegetation Index (NDVI = (NIR − Red) / (NIR + Red)). " "Reports mean greenness and the fraction of the AOI under vegetation."

    requires = Requires(bands=["red", "nir"], max_cloud_cover=40.0)

    scores = {
        "ndvi_mean": Score(
            description="Mean NDVI across all valid pixels in the AOI",
            unit="index",
            range=(-1.0, 1.0),
            primary=True,
            thresholds=Thresholds(green=(0.4, 1.0), yellow=(0.2, 0.4)),
        ),
        "vegetated_fraction": Score(
            description=f"Fraction of valid pixels with NDVI above {_VEGETATION_NDVI}",
            unit="fraction",
            range=(0.0, 1.0),
            thresholds=Thresholds(green=(0.5, 1.0), yellow=(0.2, 0.5)),
        ),
    }

    rasters = ["ndvi"]

    def _ndvi(self, bands: Bands):
        red = bands.red.mask_outside(*_REFLECTANCE_RANGE)
        nir = bands.nir.mask_outside(*_REFLECTANCE_RANGE)
        denominator = nir + red
        import numpy as np

        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = (nir - red) / denominator
        return ndvi.mask_where(np.abs(np.asarray(denominator)) <= 1e-10)

    def run(self, bands: Bands) -> dict:
        ndvi = self._ndvi(bands)
        n_valid = ndvi.valid_count
        if n_valid < _MIN_VALID_PIXELS:
            return {"ndvi_mean": None, "vegetated_fraction": None, "valid_pixel_count": n_valid}
        return {
            "ndvi_mean": round(ndvi.nanmean(), 6),
            "vegetated_fraction": round(ndvi.fraction_above(_VEGETATION_NDVI), 6),
            "valid_pixel_count": n_valid,
        }

    def derived_rasters(self, bands: Bands) -> dict:
        return {"ndvi": self._ndvi(bands)}
