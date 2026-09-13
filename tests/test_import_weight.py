import json
import subprocess
import sys

HEAVY = {"sqlalchemy", "fastapi", "celery", "boto3", "rasterio", "pystac_client", "shapely"}


def test_importing_the_sdk_pulls_in_nothing_but_numpy():
    code = "import sys, json; before=set(sys.modules); import geotriage; " f"print(json.dumps(sorted({{m.split('.')[0] for m in set(sys.modules)-before}} & {HEAVY!r})))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == []


def test_the_cli_is_importable_without_the_optional_extras():
    """`geotriage validate` must work on a bare install, so only `verify` and `test` may need more"""
    code = "import sys, json; before=set(sys.modules); import geotriage.cli; print(json.dumps(sorted({m.split('.')[0] for m in set(sys.modules)-before} & {'rasterio','pystac_client'})))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == []


def test_every_name_the_docs_tell_authors_to_import_resolves():
    """the auth strategies are the documented way to reach a private archive"""
    import geotriage

    documented = {
        "Model",
        "Requires",
        "Score",
        "Thresholds",
        "Prefilter",
        "Bands",
        "Raster",
        "Provider",
        "Collection",
        "Band",
        "Auth",
        "NoAuth",
        "BearerAuth",
        "ApiKeyAuth",
        "PlanetaryComputerSAS",
    }
    missing = sorted(name for name in documented if not hasattr(geotriage, name))
    assert not missing, f"documented but not exported: {missing}"
    assert documented <= set(geotriage.__all__), "exported but missing from __all__"
