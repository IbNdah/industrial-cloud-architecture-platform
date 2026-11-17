"""Unit tests for industrial telemetry validation and normalization."""

import math
import unittest
from datetime import datetime, timezone

from edge.industrial_gateway.telemetry_validator import normalize_telemetry


class TelemetryValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.observed_at = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
        self.valid_reading = {
            "assetId": "M-101",
            "state": "RUNNING",
            "temperature": 50.0,
            "speed": 1200.0,
            "alarm": False,
        }

    def test_normalizes_valid_reading(self) -> None:
        snapshot = normalize_telemetry(self.valid_reading, self.observed_at)

        self.assertEqual(snapshot.schema_version, "1.0")
        self.assertEqual(snapshot.asset_id, "M-101")
        self.assertEqual(snapshot.asset_type, "electric_motor")
        self.assertEqual(snapshot.state, "RUNNING")
        self.assertEqual(snapshot.temperature, 50.0)
        self.assertEqual(snapshot.speed, 1200.0)
        self.assertIs(snapshot.alarm, False)
        self.assertEqual(snapshot.observed_at, self.observed_at)

    def test_accepts_valid_readings_for_all_registered_assets(self) -> None:
        readings = [
            ("M-101", 50.0, 1200.0),
            ("M-102", 50.0, 1200.0),
            ("P-101", 45.0, 2500.0),
            ("C-101", 40.0, 100.0),
            ("F-101", 40.0, 1500.0),
        ]

        for asset_id, temperature, speed in readings:
            with self.subTest(asset_id=asset_id):
                reading = {
                    **self.valid_reading,
                    "assetId": asset_id,
                    "temperature": temperature,
                    "speed": speed,
                }
                snapshot = normalize_telemetry(reading, self.observed_at)
                self.assertEqual(snapshot.asset_id, asset_id)

    def test_accepts_stopped_asset_with_residual_temperature(self) -> None:
        reading = {
            **self.valid_reading,
            "state": "STOPPED",
            "temperature": 32.0,
            "speed": 0.0,
        }

        snapshot = normalize_telemetry(reading, self.observed_at)

        self.assertEqual(snapshot.state, "STOPPED")
        self.assertEqual(snapshot.temperature, 32.0)
        self.assertEqual(snapshot.speed, 0.0)

    def test_rejects_unknown_asset(self) -> None:
        reading = {**self.valid_reading, "assetId": "UNKNOWN"}
        with self.assertRaisesRegex(ValueError, "Unknown industrial asset"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_invalid_state(self) -> None:
        reading = {**self.valid_reading, "state": "MAINTENANCE"}
        with self.assertRaisesRegex(ValueError, "state must be"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_temperature_below_running_minimum(self) -> None:
        reading = {**self.valid_reading, "temperature": 34.9}
        with self.assertRaisesRegex(ValueError, "below the operating minimum"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_temperature_above_maximum(self) -> None:
        reading = {**self.valid_reading, "temperature": 75.1}
        with self.assertRaisesRegex(ValueError, "exceeds the maximum"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_stopped_temperature_below_minimum(self) -> None:
        reading = {
            **self.valid_reading,
            "state": "STOPPED",
            "temperature": 19.9,
            "speed": 0.0,
        }
        with self.assertRaisesRegex(ValueError, "stopped-state minimum"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_speed_above_asset_maximum(self) -> None:
        reading = {**self.valid_reading, "speed": 1500.1}
        with self.assertRaisesRegex(ValueError, "speed is outside"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_nonzero_speed_when_stopped(self) -> None:
        reading = {
            **self.valid_reading,
            "state": "STOPPED",
            "temperature": 32.0,
            "speed": 1.0,
        }
        with self.assertRaisesRegex(ValueError, "speed must be zero"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_non_boolean_alarm(self) -> None:
        reading = {**self.valid_reading, "alarm": 0}
        with self.assertRaisesRegex(ValueError, "alarm must be a boolean"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_non_numeric_temperature(self) -> None:
        reading = {**self.valid_reading, "temperature": "50"}
        with self.assertRaisesRegex(ValueError, "temperature must be a number"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_boolean_as_numeric_value(self) -> None:
        reading = {**self.valid_reading, "speed": True}
        with self.assertRaisesRegex(ValueError, "speed must be a number"):
            normalize_telemetry(reading, self.observed_at)

    def test_rejects_non_finite_values(self) -> None:
        for invalid_value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=invalid_value):
                reading = {**self.valid_reading, "temperature": invalid_value}
                with self.assertRaisesRegex(ValueError, "temperature must be finite"):
                    normalize_telemetry(reading, self.observed_at)

    def test_rejects_naive_timestamp(self) -> None:
        naive_timestamp = datetime(2026, 11, 3, 12, 0)
        with self.assertRaisesRegex(ValueError, "observed_at must be timezone-aware"):
            normalize_telemetry(self.valid_reading, naive_timestamp)

    def test_rejects_missing_required_values(self) -> None:
        for field in ("assetId", "state", "temperature", "speed", "alarm"):
            with self.subTest(field=field):
                reading = dict(self.valid_reading)
                del reading[field]
                with self.assertRaises(ValueError):
                    normalize_telemetry(reading, self.observed_at)


if __name__ == "__main__":
    unittest.main()
