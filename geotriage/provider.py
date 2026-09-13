import os
from dataclasses import dataclass, field


class Auth:
    """subclass only if none of the built-in strategies fit"""

    def headers(self) -> dict[str, str]:
        return {}

    def sign(self, href: str) -> str:
        return href


class NoAuth(Auth):
    """a public archive"""


@dataclass
class BearerAuth(Auth):
    """read from the environment at request time so the token never lives in the provider definition"""

    env: str

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {_require_env(self.env)}"}


@dataclass
class ApiKeyAuth(Auth):
    env: str
    header: str = "X-API-Key"

    def headers(self) -> dict[str, str]:
        return {self.header: _require_env(self.env)}


class PlanetaryComputerSAS(Auth):
    """Microsoft Planetary Computer hands out short-lived SAS tokens per asset"""

    def sign(self, href: str) -> str:
        import planetary_computer

        return planetary_computer.sign(href)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"environment variable '{name}' is not set, and this provider's auth needs it")
    return value


@dataclass
class Band:
    """
    calibrated value = raw * scale + offset,
    the defaults being a no-op for archives that already store physical units
    """

    normalized_name: str  # platform-independent name, e.g. "nir", "swir1"
    asset_key: str  # STAC item assets dict key, e.g. "nir08", "swir16"
    description: str = ""
    scale: float = 1.0
    offset: float = 0.0

    def calibrate(self, array):
        if self.scale == 1.0 and self.offset == 0.0:
            return array
        return array * self.scale + self.offset


@dataclass
class Collection:
    slug: str
    display_name: str
    description: str = ""
    processing_level: str = ""  # "SR", "TOA", etc.
    sensor_type: str = "multispectral"  # "multispectral", "sar", etc.
    resolution_m: float = 0.0
    cloud_cover_property: str | None = None  # STAC properties key for cloud cover
    bands: list[Band] = field(default_factory=list)

    def band(self, normalized_name: str) -> Band | None:
        return next((b for b in self.bands if b.normalized_name == normalized_name), None)


class Provider:
    slug: str
    name: str
    stac_api_url: str
    auth: Auth = NoAuth()
    collections: dict[str, Collection] = {}

    def get_client(self):
        """override only for an archive that needs something stranger than headers"""
        import pystac_client

        headers = self.auth.headers()
        return pystac_client.Client.open(self.stac_api_url, headers=headers or None)

    def sign_href(self, href: str) -> str:
        return self.auth.sign(href)
