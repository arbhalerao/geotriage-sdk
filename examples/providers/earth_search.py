from geotriage import Band, Collection, Provider

# Earth Search serves Sentinel-2 as public cloud-optimized GeoTIFFs on AWS open data,
# with reflectance scaled by 10000 and human-readable asset keys
_S2 = {"scale": 0.0001, "offset": 0.0}

_SENTINEL2_BANDS = [
    Band("coastal", "coastal", "Coastal Aerosol (60m)", **_S2),
    Band("blue", "blue", "Blue (10m)", **_S2),
    Band("green", "green", "Green (10m)", **_S2),
    Band("red", "red", "Red (10m)", **_S2),
    Band("rededge1", "rededge1", "Red Edge 1 (20m)", **_S2),
    Band("rededge2", "rededge2", "Red Edge 2 (20m)", **_S2),
    Band("rededge3", "rededge3", "Red Edge 3 (20m)", **_S2),
    Band("nir", "nir", "Near Infrared (10m)", **_S2),
    Band("nir08", "nir08", "Narrow NIR (20m)", **_S2),
    Band("swir1", "swir16", "SWIR 1 (20m)", **_S2),
    Band("swir2", "swir22", "SWIR 2 (20m)", **_S2),
]


class EarthSearchProvider(Provider):
    slug = "earth-search"
    name = "Earth Search (Element 84)"
    stac_api_url = "https://earth-search.aws.element84.com/v1"
    # public bucket — no signing, unlike Planetary Computer

    collections = {
        "sentinel-2-l2a": Collection(
            slug="sentinel-2-l2a",
            display_name="Sentinel-2 Level-2A",
            description=("ESA Copernicus Sentinel-2 surface reflectance (bottom-of-atmosphere), " "served as public cloud-optimized GeoTIFFs on AWS Open Data."),
            processing_level="SR",
            sensor_type="multispectral",
            resolution_m=10.0,
            cloud_cover_property="eo:cloud_cover",
            bands=_SENTINEL2_BANDS,
        ),
    }
