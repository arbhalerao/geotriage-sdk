from geotriage.bands import Bands, Raster
from geotriage.descriptor import describe, describe_model, describe_provider
from geotriage.compat import (
    CompatibilityResult,
    CompatReason,
    build_normalized_assets,
    check_compatibility,
)
from geotriage.model import Model, Prefilter, Requires, Score, Thresholds, split_output
from geotriage.provider import ApiKeyAuth, Auth, Band, BearerAuth, Collection, NoAuth, PlanetaryComputerSAS, Provider
from geotriage.validate import (
    check_collection,
    check_descriptor,
    check_model,
    check_provider,
)

__version__ = "0.1.0"

__all__ = [
    "ApiKeyAuth",
    "Auth",
    "Band",
    "Bands",
    "BearerAuth",
    "Collection",
    "CompatReason",
    "CompatibilityResult",
    "Model",
    "NoAuth",
    "PlanetaryComputerSAS",
    "Prefilter",
    "Provider",
    "Raster",
    "Requires",
    "Score",
    "Thresholds",
    "build_normalized_assets",
    "check_collection",
    "check_descriptor",
    "check_compatibility",
    "check_model",
    "check_provider",
    "describe",
    "describe_model",
    "describe_provider",
    "split_output",
]
