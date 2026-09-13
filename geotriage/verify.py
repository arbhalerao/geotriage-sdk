from __future__ import annotations

from geotriage.provider import Collection, Provider

SAMPLE_SIZE = 5


def _sample_items(provider: Provider, collection: Collection, limit: int = SAMPLE_SIZE):
    search = provider.get_client().search(collections=[collection.slug], max_items=limit)
    return list(search.items())


def verify_collection(provider: Provider, collection: Collection) -> list[str]:
    """
    several items, not one, because a STAC collection is not necessarily homogeneous:
    landsat-c2-l1 mixes Landsat 8/9 with 1970s MSS scenes that carry a different set of assets entirely
    so a band present in some items and absent in others still breaks models on part of the archive
    """
    try:
        items = _sample_items(provider, collection)
    except Exception as exc:
        return [f"could not reach {provider.stac_api_url}: {exc}"]

    if not items:
        return [f"the archive returned no items for '{collection.slug}' — is the slug right?"]

    problems = []
    for band in collection.bands:
        carrying = [i for i in items if band.asset_key in i.assets]
        if carrying:
            if len(carrying) < len(items):
                missing_from = next(i for i in items if band.asset_key not in i.assets)
                problems.append(
                    f"band '{band.normalized_name}' (asset '{band.asset_key}') is on "
                    f"{len(carrying)} of {len(items)} sampled items — absent from "
                    f"{missing_from.id}. Models needing it will fail on part of this "
                    f"collection; consider splitting it or narrowing the band table."
                )
            continue

        seen = {key for i in items for key in i.assets}
        suggestion = _closest(band.asset_key, seen)
        hint = f" Did you mean '{suggestion}'?" if suggestion else ""
        problems.append(f"band '{band.normalized_name}' maps to asset '{band.asset_key}', which none " f"of the {len(items)} sampled items have.{hint}")

    if collection.cloud_cover_property:
        without = [i for i in items if collection.cloud_cover_property not in i.properties]
        if len(without) == len(items):
            problems.append(f"cloud_cover_property '{collection.cloud_cover_property}' is on none of the " f"sampled items, so cloud filtering will silently pass every scene.")

    return problems


def verify_provider(provider: Provider) -> dict[str, list[str]]:
    return {slug: verify_collection(provider, c) for slug, c in provider.collections.items()}


def _closest(name: str, candidates: set[str]) -> str | None:
    import difflib

    matches = difflib.get_close_matches(name, sorted(candidates), n=1, cutoff=0.6)
    return matches[0] if matches else None
