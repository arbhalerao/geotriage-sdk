from __future__ import annotations

from typing import Any, Iterator

import numpy as np


class Raster(np.ndarray):
    """
    a float32 2-D array where NaN means nodata

    subclassing ndarray is what keeps `(bands.green - bands.nir) / (bands.green + bands.nir)`
    a Raster, so the nan-aware helpers survive arithmetic
    """

    def __new__(cls, data: Any) -> "Raster":
        return np.asarray(data, dtype=np.float32).view(cls)

    @property
    def valid(self) -> np.ndarray:
        return ~np.isnan(np.asarray(self))

    @property
    def valid_count(self) -> int:
        return int(np.count_nonzero(self.valid))

    # every reduction ignores nodata and returns None when nothing is left

    def nanmean(self) -> float | None:
        return self._reduce(np.mean)

    def nanmedian(self) -> float | None:
        return self._reduce(np.median)

    def nanmin(self) -> float | None:
        return self._reduce(np.min)

    def nanmax(self) -> float | None:
        return self._reduce(np.max)

    def nanstd(self) -> float | None:
        return self._reduce(np.std)

    def fraction_above(self, threshold: float) -> float | None:
        return self._fraction(lambda v: v > threshold)

    def fraction_below(self, threshold: float) -> float | None:
        return self._fraction(lambda v: v < threshold)

    def mask_outside(self, low: float, high: float) -> "Raster":
        arr = np.asarray(self, dtype=np.float32)
        return Raster(np.where((arr < low) | (arr > high), np.nan, arr))

    def mask_where(self, condition: np.ndarray) -> "Raster":
        arr = np.asarray(self, dtype=np.float32)
        return Raster(np.where(condition, np.nan, arr))

    def _values(self) -> np.ndarray:
        arr = np.asarray(self)
        return arr[~np.isnan(arr)]

    def _reduce(self, fn) -> float | None:
        vals = self._values()
        return float(fn(vals)) if vals.size else None

    def _fraction(self, predicate) -> float | None:
        vals = self._values()
        if not vals.size:
            return None
        return float(np.count_nonzero(predicate(vals)) / vals.size)


class Bands:
    """
    calibrated bands for one scene, addressed by normalized name

    asking for an undeclared band names what is available, because that mistake is
    otherwise a KeyError from deep inside staging
    """

    __slots__ = ("_arrays", "collection", "transform", "crs")

    def __init__(
        self,
        arrays: dict[str, Any],
        collection_slug: str,
        transform: Any = None,
        crs: Any = None,
    ) -> None:
        object.__setattr__(self, "_arrays", {k: Raster(v) for k, v in arrays.items()})
        object.__setattr__(self, "collection", collection_slug)
        object.__setattr__(self, "transform", transform)
        object.__setattr__(self, "crs", crs)

    @property
    def names(self) -> list[str]:
        return sorted(self._arrays)

    @property
    def shape(self) -> tuple[int, ...]:
        for arr in self._arrays.values():
            return arr.shape
        return ()

    def __getitem__(self, name: str) -> Raster:
        try:
            return self._arrays[name]
        except KeyError:
            raise KeyError(f"band '{name}' was not staged for this scene. " f"Available: {', '.join(self.names) or '(none)'}. " f"Declare it in the model's Requires(bands=[...]).") from None

    def __getattr__(self, name: str) -> Raster:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(str(exc)) from None

    def __contains__(self, name: str) -> bool:
        return name in self._arrays

    def __iter__(self) -> Iterator[str]:
        return iter(self.names)

    def __len__(self) -> int:
        return len(self._arrays)

    def stack(self, *names: str) -> np.ndarray:
        """stack the named bands into one (n_bands, height, width) array"""
        if not names:
            raise ValueError("stack() needs at least one band name")
        return np.stack([np.asarray(self[n]) for n in names])

    def __repr__(self) -> str:
        return f"Bands({self.collection}, {self.names}, shape={self.shape})"
