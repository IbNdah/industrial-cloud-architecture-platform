"""Registry of industrial assets available to the Edge Gateway."""

from simulator.industrial_assets.simulator import ASSETS
from simulator.industrial_assets.models import AssetConfig

ASSETS_BY_ID: dict[str, AssetConfig] = {
    asset.asset_id: asset for asset in ASSETS
}


def get_asset_config(asset_id: str) -> AssetConfig:
    """Return the registered configuration for an asset identifier."""
    try:
        return ASSETS_BY_ID[asset_id]
    except KeyError:
        raise ValueError(f"Unknown industrial asset: {asset_id}") from None
