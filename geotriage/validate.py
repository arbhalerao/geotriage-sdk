from geotriage.descriptor import DESCRIPTOR_VERSION, collection_from_descriptor
from geotriage.model import Model, Prefilter, Requires, Score
from geotriage.provider import Collection, Provider


def check_model(model: Model) -> list[str]:
    problems: list[str] = []

    if not getattr(model, "slug", ""):
        problems.append("slug is required")
    if not getattr(model, "name", ""):
        problems.append("name is required")

    requires = getattr(model, "requires", None)
    if not isinstance(requires, Requires) or not requires.bands:
        problems.append("requires must be a Requires(...) declaring at least one band")
    elif len(set(requires.bands)) != len(requires.bands):
        problems.append("requires.bands contains duplicates")

    scores = getattr(model, "scores", None)
    if not isinstance(scores, dict) or not scores:
        problems.append("scores must be a non-empty dict of name -> Score(...)")
        return problems

    primaries = [n for n, s in scores.items() if getattr(s, "primary", False)]
    if len(primaries) != 1:
        problems.append(f"exactly one score must be primary, found {len(primaries)}: {primaries}")

    for name, score in scores.items():
        if not isinstance(score, Score):
            problems.append(f"score '{name}' is not a Score(...)")
            continue
        if score.thresholds is None:
            problems.append(f"score '{name}' has no thresholds")

    if not isinstance(getattr(model, "rasters", []), list):
        problems.append("rasters must be a list of names")

    prefilter = getattr(model, "prefilter", None)
    if prefilter is not None:
        if not isinstance(prefilter, Prefilter):
            problems.append("prefilter must be a Prefilter(...)")
        else:
            if not prefilter.bands:
                problems.append("prefilter declares no bands")
            if prefilter.gsd_m <= 0:
                problems.append("prefilter needs a positive gsd_m")
            if type(model).screen is Model.screen:
                problems.append("a prefilter is declared but screen() is not implemented, so every " "scene would pass the gate")

    return problems


def check_collection(collection: Collection) -> list[str]:
    problems: list[str] = []

    if not collection.slug:
        problems.append("collection slug is required")
    if not collection.bands:
        problems.append(f"collection '{collection.slug}' declares no bands")

    seen: set[str] = set()
    for band in collection.bands:
        if not band.normalized_name:
            problems.append(f"collection '{collection.slug}' has a band with no normalized_name")
        if not band.asset_key:
            problems.append(f"band '{band.normalized_name}' has no asset_key")
        if band.normalized_name in seen:
            problems.append(f"band '{band.normalized_name}' is declared twice")
        seen.add(band.normalized_name)
        if band.scale == 0:
            problems.append(f"band '{band.normalized_name}' has scale 0, which zeroes the data")

    if collection.resolution_m <= 0:
        problems.append(f"collection '{collection.slug}' needs a positive resolution_m")

    return problems


def check_provider(provider: Provider) -> list[str]:
    """
    structural checks only,
    whether the declared asset keys exist on real items needs the network and is `geotriage verify`
    """
    problems: list[str] = []

    if not getattr(provider, "slug", ""):
        problems.append("slug is required")
    if not getattr(provider, "name", ""):
        problems.append("name is required")
    if not getattr(provider, "stac_api_url", ""):
        problems.append("stac_api_url is required")

    collections = getattr(provider, "collections", None)
    if not isinstance(collections, dict) or not collections:
        problems.append("collections must be a non-empty dict of slug -> Collection(...)")
        return problems

    for slug, collection in collections.items():
        if not isinstance(collection, Collection):
            problems.append(f"collections['{slug}'] is not a Collection(...)")
            continue
        if collection.slug != slug:
            problems.append(f"collections['{slug}'] declares slug '{collection.slug}'")
        problems.extend(check_collection(collection))

    return problems


# an image can't be imported,
# so the platform applies the same rules to the JSON it describes itself with

_KINDS = ("model", "provider")


def check_descriptor(data: object) -> list[str]:
    if not isinstance(data, dict):
        return [f"a descriptor must be a JSON object, got {type(data).__name__}"]

    kind = data.get("kind")
    if kind not in _KINDS:
        return [f"kind must be one of {list(_KINDS)}, got {kind!r}"]

    version = data.get("descriptor_version")
    if version != DESCRIPTOR_VERSION:
        return [f"descriptor_version {version!r} is not supported (this platform speaks " f"{DESCRIPTOR_VERSION}). Rebuild against a matching geotriage-sdk base image."]

    return _check_model_descriptor(data) if kind == "model" else _check_provider_descriptor(data)


def _check_model_descriptor(data: dict) -> list[str]:
    problems: list[str] = []
    for field in ("slug", "name"):
        if not data.get(field):
            problems.append(f"{field} is required")

    requires = data.get("requires")
    if not isinstance(requires, dict) or not requires.get("bands"):
        problems.append("requires.bands must list at least one band")
    elif len(set(requires["bands"])) != len(requires["bands"]):
        problems.append("requires.bands contains duplicates")

    scores = data.get("scores")
    if not isinstance(scores, dict) or not scores:
        problems.append("scores must be a non-empty object")
        return problems

    primaries = [n for n, s in scores.items() if isinstance(s, dict) and s.get("primary")]
    if len(primaries) != 1:
        problems.append(f"exactly one score must be primary, found {len(primaries)}: {primaries}")

    for name, score in scores.items():
        if not isinstance(score, dict):
            problems.append(f"score '{name}' must be an object")
            continue
        thresholds = score.get("thresholds")
        if not isinstance(thresholds, dict):
            problems.append(f"score '{name}' has no thresholds")
            continue
        for band in ("green", "yellow"):
            pair = thresholds.get(band)
            if not (isinstance(pair, list) and len(pair) == 2):
                problems.append(f"score '{name}' threshold '{band}' must be a [min, max] pair")

    prefilter = data.get("prefilter")
    if prefilter is not None:
        if not isinstance(prefilter, dict) or not prefilter.get("bands"):
            problems.append("prefilter must declare bands")
        elif not (isinstance(prefilter.get("gsd_m"), (int, float)) and prefilter["gsd_m"] > 0):
            problems.append("prefilter needs a positive gsd_m")

    return problems


def _check_provider_descriptor(data: dict) -> list[str]:
    problems: list[str] = []
    for field in ("slug", "name", "stac_api_url"):
        if not data.get(field):
            problems.append(f"{field} is required")

    collections = data.get("collections")
    if not isinstance(collections, dict) or not collections:
        problems.append("collections must be a non-empty object")
        return problems

    for slug, collection in collections.items():
        if not isinstance(collection, dict):
            problems.append(f"collections['{slug}'] must be an object")
            continue
        if collection.get("slug") != slug:
            problems.append(f"collections['{slug}'] declares slug {collection.get('slug')!r}")
        problems.extend(check_collection(collection_from_descriptor(collection)))

    return problems
