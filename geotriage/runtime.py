from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from typing import Any

MODEL_ENV = "GEOTRIAGE_MODEL"
PROVIDER_ENV = "GEOTRIAGE_PROVIDER"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_ERROR = 3


def declared_target() -> tuple[str, str]:
    """
    (env var, target) for whichever of the two the image declares

    requiring exactly one is what lets the platform know an image's kind from its
    environment, before it has run anything
    """
    declared = {name: os.environ.get(name, "").strip() for name in (MODEL_ENV, PROVIDER_ENV)}
    set_vars = {name: value for name, value in declared.items() if value}

    if not set_vars:
        raise SystemExit(f"neither {MODEL_ENV} nor {PROVIDER_ENV} is set. An image must declare the class to load, " f"e.g. ENV {MODEL_ENV}=mypkg.detectors:ShipDetector")
    if len(set_vars) > 1:
        raise SystemExit(f"both {MODEL_ENV} and {PROVIDER_ENV} are set. An image is one or the other, never both.")

    return next(iter(set_vars.items()))


def load_declared(target: str | None = None):
    if target is None:
        env_name, target = declared_target()
    else:
        env_name = "target"
    if ":" not in target:
        raise SystemExit(f"{env_name}='{target}' should look like 'package.module:ClassName'")

    module_name, _, attr = target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"could not import '{module_name}': {exc}") from None
    try:
        obj = getattr(module, attr)
    except AttributeError:
        defines = ", ".join(n for n in vars(module) if not n.startswith("_")) or "(nothing)"
        raise SystemExit(f"'{module_name}' has no '{attr}'. It defines: {defines}") from None
    return obj() if isinstance(obj, type) else obj


def _read(path: str) -> dict[str, Any]:
    with open(path) as handle:
        return json.load(handle)


def _write(path: str, payload: dict[str, Any]) -> None:
    with open(path, "w") as handle:
        json.dump(payload, handle)


def _bands_from_job(job: dict[str, Any]):
    import rasterio

    from geotriage.bands import Bands

    arrays, transform, crs = {}, None, None
    for name, path in job["bands"].items():
        with rasterio.open(path) as src:
            arrays[name] = src.read(1)
            if transform is None:
                transform, crs = src.transform, src.crs
    return Bands(
        arrays,
        collection_slug=job.get("collection_slug", ""),
        transform=transform,
        crs=crs,
    )


def cmd_describe(_args) -> int:
    from geotriage.descriptor import describe

    print(json.dumps(describe(load_declared()), indent=2))
    return EXIT_OK


def cmd_run(args) -> int:
    from geotriage.model import split_output

    model = load_declared()
    job = _read(args.job)
    bands = _bands_from_job(job)

    output = model.run(bands)
    scores, metadata = split_output(model, output)  # raises on a missing declared score

    rasters = {}
    out_dir = job.get("raster_dir")
    if out_dir and model.rasters:
        import rasterio

        for name, array in model.derived_rasters(bands).items():
            path = os.path.join(out_dir, f"{name}.tif")
            _write_raster(rasterio, path, array, bands.transform, bands.crs)
            rasters[name] = path

    _write(args.out, {"scores": scores, "metadata": metadata, "rasters": rasters})
    return EXIT_OK


def _write_raster(rasterio, path, array, transform, crs) -> None:
    import numpy as np

    data = np.asarray(array, dtype="float32")
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": int(data.shape[0]),
        "width": int(data.shape[1]),
        "transform": transform,
        "crs": crs,
        "nodata": float("nan"),
        "compress": "DEFLATE",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)


def cmd_screen(args) -> int:
    model = load_declared()
    job = _read(args.job)
    keep = bool(model.screen(_bands_from_job(job)))
    _write(args.out, {"keep": keep})
    return EXIT_OK


def cmd_search(args) -> int:
    provider = load_declared()
    job = _read(args.job)

    kwargs: dict[str, Any] = {"collections": [job["collection_slug"]]}
    for key in ("intersects", "datetime", "query", "ids"):
        if job.get(key) is not None:
            kwargs[key] = job[key]
    kwargs["max_items"] = int(job.get("max_items", 500))

    items = [item.to_dict() for item in provider.get_client().search(**kwargs).items()]
    print(json.dumps({"items": items}))
    return EXIT_OK


def cmd_sign(args) -> int:
    """a container start per band would cost more than the download it enables"""
    provider = load_declared()
    job = _read(args.job)
    print(json.dumps({"hrefs": [provider.sign_href(h) for h in job["hrefs"]]}))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geotriage", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("describe").set_defaults(func=cmd_describe)

    p_run = sub.add_parser("run")
    p_run.add_argument("--job", required=True)
    p_run.add_argument("--out", required=True)
    p_run.set_defaults(func=cmd_run)

    p_screen = sub.add_parser("screen")
    p_screen.add_argument("--job", required=True)
    p_screen.add_argument("--out", required=True)
    p_screen.set_defaults(func=cmd_screen)

    p_search = sub.add_parser("search")
    p_search.add_argument("--job", required=True)
    p_search.set_defaults(func=cmd_search)

    p_sign = sub.add_parser("sign")
    p_sign.add_argument("--job", required=True)
    p_sign.set_defaults(func=cmd_sign)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SystemExit:
        raise
    except Exception as exc:
        # stderr is captured by the platform and shown to whoever registered the image, so keep it legible
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
