from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from geotriage.bands import Bands


@dataclass
class Requires:
    bands: list[str]  # normalized band names, e.g. ["green", "nir"]
    max_cloud_cover: float | None = None  # skip scenes cloudier than this, when reported

    # None means native resolution; declaring a value lets the platform read a COG
    # overview instead of the full scene, which is most of the cost of a workflow
    gsd_m: float | None = None

    cost: str = "medium"  # "low" | "medium" | "high" — a scheduling hint, not a promise


@dataclass
class Prefilter:
    """
    declaring one obliges the model to implement `screen(bands) -> bool`,
    which is asked first off a coarse overview so an uninteresting scene is dropped
    before anything is fetched at full resolution
    """

    bands: list[str]
    gsd_m: float  # deliberately coarse; this is the point


@dataclass
class Thresholds:
    """
    severity bands for one score

    red is the fall-through, so there is no red band to declare
    """

    green: tuple[float, float]
    yellow: tuple[float, float]


@dataclass
class Score:
    description: str = ""
    unit: str = ""  # e.g. "index", "fraction", "count", "°C"
    range: tuple[float, float] = (-1.0, 1.0)
    primary: bool = False  # the score that drives the scene's overall severity
    thresholds: Thresholds | None = None


class Model(ABC):
    slug: str
    name: str
    description: str = ""

    requires: Requires
    scores: dict[str, Score]
    rasters: list[str] = []  # per-pixel outputs published by derived_rasters()
    prefilter: Prefilter | None = None  # declare one to enable screen()

    @abstractmethod
    def run(self, bands: Bands) -> dict[str, Any]:
        """
        `bands` carries calibrated, AOI-clipped rasters in physical units, NaN being nodata
        return a dict containing every declared score name,
        None is allowed when a scene has too little data
        any other key is kept as run metadata
        """
        ...

    def screen(self, bands: Bands) -> bool:
        """
        only called when `prefilter` is declared, with its bands at roughly its declared resolution

        return False to skip the scene without ever fetching it at full resolution
        """
        return True

    def derived_rasters(self, bands: Bands) -> dict[str, Any]:
        """
        keyed by name and matching `rasters`,
        each a float32 array with the same shape and georeferencing as the input bands
        """
        return {}

    @property
    def primary_score(self) -> str:
        for name, score in self.scores.items():
            if score.primary:
                return name
        raise ValueError(f"model '{self.slug}' declares no primary score")

    @property
    def default_thresholds(self) -> dict[str, Thresholds]:
        return {n: s.thresholds for n, s in self.scores.items() if s.thresholds is not None}


def split_output(model: Model, output: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """the declared set must all be present, otherwise a misspelled score name vanishes silently"""
    if not isinstance(output, dict):
        raise ValueError(f"{model.slug}.run() must return a dict, got {type(output).__name__}")

    declared = set(model.scores)
    missing = declared - set(output)
    if missing:
        raise ValueError(f"{model.slug}.run() did not return declared score(s): {sorted(missing)}. " f"It returned: {sorted(output)}.")

    scores = {name: output[name] for name in declared}
    metadata = {k: v for k, v in output.items() if k not in declared}
    return scores, metadata
