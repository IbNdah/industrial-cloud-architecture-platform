"""Generate simulated telemetry for industrial assets."""

import random
from datetime import UTC, datetime

from .models import AssetConfig, Telemetry

ASSETS = (
    AssetConfig("M-101", "electric_motor", 35.0, 75.0, 0.0, 1500.0, 70.0),
    AssetConfig("M-102", "electric_motor", 35.0, 75.0, 0.0, 1500.0, 70.0),
    AssetConfig("P-101", "pump", 30.0, 65.0, 0.0, 3000.0, 60.0),
    AssetConfig("C-101", "conveyor", 25.0, 55.0, 0.0, 120.0, 50.0),
    AssetConfig("F-101", "fan", 25.0, 60.0, 0.0, 1800.0, 55.0),
)


class IndustrialSimulator:
    """Generate telemetry snapshots for configured industrial assets."""

    def __init__(
        self, assets: tuple[AssetConfig, ...] = ASSETS, seed: int | None = None
    ):
        self.assets = assets
        self.random = random.Random(seed)

    def generate_telemetry(self, asset: AssetConfig) -> Telemetry:
        """Generate one telemetry snapshot for an asset."""
        state = self.random.choices(
            ["RUNNING", "STOPPED"],
            weights=[0.9, 0.1],
            k=1,
        )[0]

        if state == "RUNNING":
            temperature = self.random.uniform(
                asset.temperature_min, asset.temperature_max
            )
            speed = self.random.uniform(asset.speed_min, asset.speed_max)
        else:
            temperature = self.random.uniform(20.0, asset.temperature_min)
            speed = 0.0

        return Telemetry(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type,
            timestamp=datetime.now(UTC),
            state=state,
            temperature=round(temperature, 2),
            speed=round(speed, 2),
            alarm=temperature >= asset.alarm_temperature,
        )

    def generate_fleet_telemetry(self) -> list[Telemetry]:
        """Generate one telemetry snapshot for every configured asset."""
        return [self.generate_telemetry(asset) for asset in self.assets]
