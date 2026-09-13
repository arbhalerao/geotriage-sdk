# A provider says where scenes come from, and how each of its assets maps onto a
# normalized band name in physical units.
#
# Copy this file, fill in the marked parts, then check it against the live archive:
#
#     geotriage validate provider:MyArchive     # declarations only, no network
#     geotriage verify   provider:MyArchive     # fetches real items and proves the
#                                               # asset keys below actually exist
#
# `verify` is the one that matters. A wrong asset_key is the most common mistake
# here and otherwise goes uncaught until a workflow is running, then fails once per
# scene.

from geotriage import Band, Collection, Provider


class MyArchive(Provider):
    slug = "my-archive"
    name = "My Archive"
    stac_api_url = "https://stac.example.com/v1"

    # For a private archive, pick one:
    #
    #   from geotriage import BearerAuth, ApiKeyAuth, PlanetaryComputerSAS
    #
    #   auth = BearerAuth(env="MY_ARCHIVE_TOKEN")
    #   auth = ApiKeyAuth(env="MY_ARCHIVE_KEY", header="X-API-Key")
    #   auth = PlanetaryComputerSAS()
    #
    # The token is read from the environment at request time, so it never lives in
    # this file. The default is a public archive that needs no credentials.

    collections = {
        # The key and the Collection's own slug must match. A collection slug names
        # exactly one archive across the whole platform, so pick something specific:
        # registering a slug another provider already owns is refused.
        "my-collection": Collection(
            slug="my-collection",
            display_name="My Collection",
            description="What this collection holds.",
            processing_level="SR",
            sensor_type="multispectral",
            resolution_m=10.0,
            # The STAC properties key this archive reports cloud cover under. Leave
            # None if it reports none; cloud filtering is then skipped rather than
            # silently passing every scene.
            cloud_cover_property="eo:cloud_cover",
            bands=[
                # Band(normalized_name, asset_key, description, scale, offset)
                #
                #   normalized_name  what a model asks for: "green", "nir", ...
                #   asset_key        the key in this archive's STAC item assets
                #   scale / offset   calibrated = raw * scale + offset
                #
                # Scale and offset are yours, not the model's: a detector asks for
                # "green" and receives reflectance whichever archive it came from.
                # Leave them at 1.0 / 0.0 if the archive already stores physical units.
                Band("green", "green", "Green", scale=0.0001, offset=0.0),
                Band("nir", "nir", "Near Infrared", scale=0.0001, offset=0.0),
            ],
        ),
    }
