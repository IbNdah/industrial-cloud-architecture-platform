"""Tests for the industrial asset simulator."""

import unittest

from simulator.industrial_assets.models import AssetConfig
from simulator.industrial_assets.simulator import ASSETS, IndustrialSimulator


class TestIndustrialSimulator(unittest.TestCase):
    def setUp(self):
        self.simulator = IndustrialSimulator(seed=42)

    def test_generates_telemetry_for_all_assets(self):
        telemetry = self.simulator.generate_fleet_telemetry()

        self.assertEqual(len(telemetry), 5)
        self.assertEqual(
            {item.asset_id for item in telemetry},
            {asset.asset_id for asset in ASSETS},
        )

    def test_telemetry_values_are_valid(self):
        telemetry = self.simulator.generate_fleet_telemetry()

        for item in telemetry:
            self.assertIn(item.state, ("RUNNING", "STOPPED"))
            self.assertGreaterEqual(item.temperature, 0)
            self.assertGreaterEqual(item.speed, 0)
            self.assertEqual(
                item.alarm,
                item.temperature
                >= next(
                    asset.alarm_temperature
                    for asset in ASSETS
                    if asset.asset_id == item.asset_id
                ),
            )

    def test_stopped_asset_has_zero_speed(self):
        stopped_asset = AssetConfig(
            asset_id="TEST-001",
            asset_type="test_asset",
            temperature_min=30.0,
            temperature_max=60.0,
            speed_min=0.0,
            speed_max=100.0,
            alarm_temperature=55.0,
        )
        simulator = IndustrialSimulator(assets=(stopped_asset,), seed=1)

        for _ in range(100):
            telemetry = simulator.generate_telemetry(stopped_asset)
            if telemetry.state == "STOPPED":
                self.assertEqual(telemetry.speed, 0.0)
                return

        self.fail("No STOPPED state generated in 100 attempts")


if __name__ == "__main__":
    unittest.main()
