from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any

from geotriage.model import Model
from geotriage.provider import Provider
from geotriage.validate import check_model, check_provider

_OK = "ok"
_FAIL = "FAIL"


def load_object(target: str) -> Any:
    """import `package.module:Name` and instantiate it if it's a class"""
    if ":" not in target:
        raise SystemExit(f"'{target}' should look like 'package.module:ClassName' — " "the module to import, then the class inside it.")
    module_name, _, attr = target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"could not import '{module_name}': {exc}") from None
    try:
        obj = getattr(module, attr)
    except AttributeError:
        available = ", ".join(n for n in vars(module) if not n.startswith("_")) or "(nothing)"
        raise SystemExit(f"'{module_name}' has no '{attr}'. It defines: {available}") from None
    return obj() if isinstance(obj, type) else obj


def report(title: str, problems: list[str]) -> int:
    if not problems:
        print(f"{_OK}  {title}")
        return 0
    print(f"{_FAIL}  {title}")
    for problem in problems:
        print(f"      - {problem}")
    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    obj = load_object(args.target)
    if isinstance(obj, Model):
        return report(f"model '{getattr(obj, 'slug', '?')}'", check_model(obj))
    if isinstance(obj, Provider):
        return report(f"provider '{getattr(obj, 'slug', '?')}'", check_provider(obj))
    raise SystemExit(f"'{args.target}' is neither a Model nor a Provider — it is {type(obj).__name__}.")


def cmd_verify(args: argparse.Namespace) -> int:
    from geotriage.verify import verify_provider

    provider = load_object(args.target)
    if not isinstance(provider, Provider):
        raise SystemExit(f"'{args.target}' is not a Provider.")

    exit_code = report(f"provider '{provider.slug}' declarations", check_provider(provider))
    for collection_slug, problems in verify_provider(provider).items():
        exit_code |= report(f"collection '{collection_slug}' against the live archive", problems)
    return exit_code


def cmd_test(args: argparse.Namespace) -> int:
    from geotriage.model import split_output
    from geotriage.sample import load_scene

    model = load_object(args.target)
    if not isinstance(model, Model):
        raise SystemExit(f"'{args.target}' is not a Model.")

    problems = check_model(model)
    if problems:
        return report(f"model '{model.slug}'", problems)

    provider = load_object(args.provider)
    if not isinstance(provider, Provider):
        raise SystemExit(f"'{args.provider}' is not a Provider.")

    collection = _pick_collection(provider, args.collection)
    missing = [b for b in model.requires.bands if collection.band(b) is None]
    if missing:
        have = ", ".join(sorted(b.normalized_name for b in collection.bands))
        raise SystemExit(f"'{collection.slug}' has no {missing} band(s). It offers: {have}.")

    print(f"    reading {collection.slug} at ~{args.gsd:g} m ...")
    try:
        item, bands = load_scene(model, provider, collection, args.scene, args.gsd)
    except Exception as exc:
        raise SystemExit(f"{_FAIL}  could not load a scene: {exc}") from None

    print(f"    scene {item.id}  shape {bands.shape}  bands {bands.names}")

    try:
        output = model.run(bands)
        scores, metadata = split_output(model, output)
    except Exception as exc:
        print(f"{_FAIL}  {model.slug}.run() raised {type(exc).__name__}: {exc}")
        return 1

    print(f"{_OK}  {model.slug} on {item.id}")
    for name, value in scores.items():
        score = model.scores[name]
        severity = _severity(value, score)
        shown = "None (too little valid data)" if value is None else f"{value:.6g}"
        print(f"      {name:<20} {shown:>28}  {severity}{'  (primary)' if score.primary else ''}")
    for name, value in metadata.items():
        print(f"      {name:<20} {value!r:>28}  (metadata)")
    return 0


def _pick_collection(provider: Provider, requested: str | None):
    if requested:
        if requested not in provider.collections:
            have = ", ".join(sorted(provider.collections))
            raise SystemExit(f"'{provider.slug}' has no collection '{requested}'. It has: {have}.")
        return provider.collections[requested]
    if len(provider.collections) == 1:
        return next(iter(provider.collections.values()))
    have = ", ".join(sorted(provider.collections))
    raise SystemExit(f"'{provider.slug}' offers several collections; pass --collection. Choices: {have}.")


def _severity(value, score) -> str:
    """what the platform would colour this, using the model's own default thresholds"""
    if value is None or score.thresholds is None:
        return "-"
    low, high = score.thresholds.green
    if low <= value <= high:
        return "green"
    low, high = score.thresholds.yellow
    if low <= value <= high:
        return "yellow"
    return "red"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geotriage", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="check a model or provider's declarations")
    p_validate.add_argument("target", help="package.module:ClassName")
    p_validate.set_defaults(func=cmd_validate)

    p_verify = sub.add_parser("verify", help="check a provider against its live archive")
    p_verify.add_argument("target", help="package.module:ClassName")
    p_verify.set_defaults(func=cmd_verify)

    p_test = sub.add_parser("test", help="run a model over one real scene")
    p_test.add_argument("target", help="package.module:ModelClass")
    p_test.add_argument("--provider", required=True, help="package.module:ProviderClass")
    p_test.add_argument("--collection", help="collection slug (optional if the provider has one)")
    p_test.add_argument("--scene", help="STAC item id (default: the most recent)")
    p_test.add_argument(
        "--gsd",
        type=float,
        default=300.0,
        help="target ground sample distance in metres; coarser is faster (default: 300)",
    )
    p_test.set_defaults(func=cmd_test)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
