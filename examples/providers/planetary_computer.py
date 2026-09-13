from geotriage import Band, Collection, Provider
from geotriage.provider import PlanetaryComputerSAS

# USGS Landsat collection 2 rescaling
# optical bands carry surface reflectance; lwir11 carries surface temperature in Kelvin
_L_OPTICAL = {"scale": 0.0000275, "offset": -0.2}
_L_THERMAL = {"scale": 0.00341802, "offset": 149.0}

# landsat-c2-l1 on Planetary Computer is the MSS archive (Landsat 1-5): green, red and
# two NIR bands, and nothing else -- it does not carry L2's band set
_MSS_BANDS = [
    Band("green", "green", "Green (MSS Band 4/1)", **_L_OPTICAL),
    Band("red", "red", "Red (MSS Band 5/2)", **_L_OPTICAL),
    Band("nir", "nir08", "Near Infrared (MSS Band 6/3)", **_L_OPTICAL),
]

_LANDSAT_BANDS = [
    Band("coastal", "coastal", "Coastal/Aerosol (Band 1)", **_L_OPTICAL),
    Band("blue", "blue", "Blue (Band 2)", **_L_OPTICAL),
    Band("green", "green", "Green (Band 3)", **_L_OPTICAL),
    Band("red", "red", "Red (Band 4)", **_L_OPTICAL),
    Band("nir", "nir08", "Near Infrared (Band 5)", **_L_OPTICAL),
    Band("swir1", "swir16", "Short-wave Infrared 1 (Band 6)", **_L_OPTICAL),
    Band("swir2", "swir22", "Short-wave Infrared 2 (Band 7)", **_L_OPTICAL),
    Band("thermal1", "lwir11", "Thermal Infrared 1 (Band 10), Kelvin", **_L_THERMAL),
]


class PlanetaryComputerProvider(Provider):
    slug = "planetary-computer"
    name = "Microsoft Planetary Computer"
    stac_api_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
    auth = PlanetaryComputerSAS()

    collections = {
        "landsat-c2-l2": Collection(
            slug="landsat-c2-l2",
            display_name="Landsat Collection 2 Level-2",
            description=("Landsat Collection 2 surface reflectance and surface temperature " "science products produced by USGS."),
            processing_level="SR",
            sensor_type="multispectral",
            resolution_m=30.0,
            cloud_cover_property="eo:cloud_cover",
            bands=_LANDSAT_BANDS,
        ),
        "landsat-c2-l1": Collection(
            slug="landsat-c2-l1",
            display_name="Landsat Collection 2 Level-1 (MSS)",
            description=("Landsat Collection 2 Level-1 Multispectral Scanner products from " "Landsat 1-5, produced by USGS."),
            processing_level="TOA",
            sensor_type="multispectral",
            resolution_m=30.0,
            cloud_cover_property="eo:cloud_cover",
            # MSS L1 is top-of-atmosphere DN whose radiometric rescaling is per-scene
            # metadata, not a fixed pair of coefficients, so indices computed from these
            # are indicative rather than calibrated
            bands=_MSS_BANDS,
        ),
    }
