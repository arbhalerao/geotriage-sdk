# A model scores one scene and returns the numbers it declared.
#
# Copy this file, fill in the marked parts, then check it without a platform:
#
#     geotriage validate model:MyDetector
#     geotriage test     model:MyDetector --provider <provider>:<Class>
#
# As written this is conformant and runnable, so `validate` passes before you
# change anything. Edit downward from the top.

from typing import Any

from geotriage import Model, Requires, Score, Thresholds
from geotriage.bands import Bands


class MyDetector(Model):
    # Identity. The slug is what workflows store, so it has to be stable and unique.
    slug = "my-detector"
    name = "My Detector"
    description = "One sentence on what this looks for."

    # What a scene must provide before this model can run against it.
    #   bands           normalized names, e.g. "green", "nir", "swir1", "thermal1"
    #   max_cloud_cover skip scenes cloudier than this, when the archive reports it
    #   gsd_m           coarsest resolution you tolerate; leave None for native.
    #                   Setting it lets the platform read a COG overview instead of
    #                   the full scene, which is most of the cost of a workflow.
    requires = Requires(bands=["green", "nir"], max_cloud_cover=30.0, gsd_m=None)

    # What you produce. Exactly one score must be primary: it drives the scene's
    # severity, which is what an analyst sorts by.
    #
    # A value inside `green` is green, inside `yellow` is yellow, and anything else
    # is red. There is no red band to declare: red is the fall-through, and red is
    # the scene someone opens.
    scores = {
        "my_index": Score(
            description="What this number means.",
            unit="index",
            range=(-1.0, 1.0),
            primary=True,
            thresholds=Thresholds(green=(0.3, 1.0), yellow=(0.0, 0.3)),
        ),
    }

    # Per-pixel outputs to publish alongside the scores. Leave empty if you have none;
    # every name listed here must be returned by derived_rasters().
    rasters: list[str] = []

    def run(self, bands: Bands) -> dict[str, Any]:
        # `bands.green` is a float32 array where NaN means nodata, already clipped to
        # the AOI and calibrated to physical units. Arithmetic keeps it that way, so
        # the nan-aware helpers survive: nanmean, nanmedian, fraction_above,
        # mask_outside, valid_count, ...
        index = (bands.green - bands.nir) / (bands.green + bands.nir)

        # Return None rather than a wrong number when a scene is too empty to judge.
        if index.valid_count < 10:
            return {"my_index": None}

        # Every declared score must appear. Any extra key is kept as run metadata,
        # which is a good place for counts you want to see later.
        return {
            "my_index": index.nanmean(),
            "valid_pixel_count": index.valid_count,
        }

    def derived_rasters(self, bands: Bands) -> dict[str, Any]:
        # Only called when `rasters` is non-empty. Return one float32 array per name,
        # the same shape as the input bands.
        return {}
