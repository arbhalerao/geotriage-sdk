from __future__ import annotations

from typing import Any

from geotriage.model import Model
from geotriage.provider import Collection, Provider

# bumped when the JSON shape changes in a way an older platform can't read
DESCRIPTOR_VERSION = 1


def describe_model(model: Model) -> dict[str, Any]:
    return {
        "descriptor_version": DESCRIPTOR_VERSION,
        "kind": "model",
        "slug": model.slug,
        "name": model.name,
        "description": getattr(model, "description", ""),
        "requires": {
            "bands": list(model.requires.bands),
            "max_cloud_cover": model.requires.max_cloud_cover,
            "gsd_m": model.requires.gsd_m,
            "cost": model.requires.cost,
        },
        "prefilter": (None if model.prefilter is None else {"bands": list(model.prefilter.bands), "gsd_m": model.prefilter.gsd_m}),
        "scores": {
            name: {
                "description": score.description,
                "unit": score.unit,
                "range": list(score.range),
                "primary": score.primary,
                "thresholds": (
                    None
                    if score.thresholds is None
                    else {
                        "green": list(score.thresholds.green),
                        "yellow": list(score.thresholds.yellow),
                    }
                ),
            }
            for name, score in model.scores.items()
        },
        "rasters": list(model.rasters),
    }


def describe_collection(collection: Collection) -> dict[str, Any]:
    return {
        "slug": collection.slug,
        "display_name": collection.display_name,
        "description": collection.description,
        "processing_level": collection.processing_level,
        "sensor_type": collection.sensor_type,
        "resolution_m": collection.resolution_m,
        "cloud_cover_property": collection.cloud_cover_property,
        "bands": [
            {
                "normalized_name": band.normalized_name,
                "asset_key": band.asset_key,
                "description": band.description,
                "scale": band.scale,
                "offset": band.offset,
            }
            for band in collection.bands
        ],
    }


def describe_provider(provider: Provider) -> dict[str, Any]:
    return {
        "descriptor_version": DESCRIPTOR_VERSION,
        "kind": "provider",
        "slug": provider.slug,
        "name": provider.name,
        "stac_api_url": provider.stac_api_url,
        "auth": type(provider.auth).__name__,
        "collections": {slug: describe_collection(c) for slug, c in provider.collections.items()},
    }


def describe(obj: Model | Provider) -> dict[str, Any]:
    if isinstance(obj, Model):
        return describe_model(obj)
    if isinstance(obj, Provider):
        return describe_provider(obj)
    raise TypeError(f"{type(obj).__name__} is neither a Model nor a Provider")


def collection_from_descriptor(data: dict[str, Any]) -> Collection:
    """
    the platform needs real collection objects to calibrate bands and check compatibility,
    even when the provider itself lives in a container it can't import
    """
    from geotriage.provider import Band

    return Collection(
        slug=data["slug"],
        display_name=data.get("display_name", data["slug"]),
        description=data.get("description", ""),
        processing_level=data.get("processing_level", ""),
        sensor_type=data.get("sensor_type", "multispectral"),
        resolution_m=float(data.get("resolution_m") or 0.0),
        cloud_cover_property=data.get("cloud_cover_property"),
        bands=[
            Band(
                normalized_name=b["normalized_name"],
                asset_key=b["asset_key"],
                description=b.get("description", ""),
                scale=float(b.get("scale", 1.0)),
                offset=float(b.get("offset", 0.0)),
            )
            for b in data.get("bands", [])
        ],
    )
