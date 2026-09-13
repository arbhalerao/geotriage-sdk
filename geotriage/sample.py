from __future__ import annotations

from typing import Any

import numpy as np

from geotriage.bands import Bands
from geotriage.compat import build_normalized_assets
from geotriage.model import Model
from geotriage.provider import Collection, Provider

DEFAULT_GSD_M = 300.0


def find_item(provider: Provider, collection: Collection, scene_id: str | None):
    client = provider.get_client()
    if scene_id:
        found = next(iter(client.search(collections=[collection.slug], ids=[scene_id]).items()), None)
        if found is None:
            raise LookupError(f"'{scene_id}' is not in collection '{collection.slug}'")
        return found

    found = next(iter(client.search(collections=[collection.slug], max_items=1).items()), None)
    if found is None:
        raise LookupError(f"collection '{collection.slug}' returned no items")
    return found


def read_band(href: str, sign, native_gsd_m: float, target_gsd_m: float):
    """read a whole scene at roughly `target_gsd_m`, via the coarsest usable overview"""
    import rasterio

    url = f"/vsicurl/{sign(href)}"
    with rasterio.open(url) as probe:
        decimations = probe.overviews(1)
        level = None
        if native_gsd_m > 0 and decimations:
            usable = [i for i, f in enumerate(decimations) if native_gsd_m * f <= target_gsd_m]
            level = max(usable) if usable else None

    opener = rasterio.open(url, overview_level=level) if level is not None else rasterio.open(url)
    with opener as src:
        data = src.read(1).astype(np.float32)
        nodata = src.nodata
        if nodata is not None:
            data[data == nodata] = np.nan
        return data, src.transform, src.crs


def load_scene(
    model: Model,
    provider: Provider,
    collection: Collection,
    scene_id: str | None = None,
    gsd_m: float = DEFAULT_GSD_M,
) -> tuple[Any, Bands]:
    item = find_item(provider, collection, scene_id)

    assets = build_normalized_assets({k: v.to_dict() for k, v in item.assets.items()}, collection, model.requires.bands)

    arrays, transform, crs = {}, None, None
    for name, asset in assets.items():
        raw, t, c = read_band(asset["href"], provider.sign_href, collection.resolution_m, gsd_m)
        arrays[name] = collection.band(name).calibrate(raw)
        if transform is None:
            transform, crs = t, c

    return item, Bands(arrays, collection_slug=collection.slug, transform=transform, crs=crs)
