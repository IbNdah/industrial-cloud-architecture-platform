"""Validation and normalization of telemetry received from OPC UA."""

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping

from edge.industrial_gateway.asset_registry import get_asset_config
from edge.industrial_gateway.telemetry import TelemetrySnapshot


SCHEMA_VERSION = "1.0"
STOPPED_TEMPERATURE_MIN = 20.0


def _read_number(value: Any, field_name: str) -> float:
    """Accept finite numeric values but reject booleans and non-numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")

    normalized = float(value)
    if not isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")

    return normalized


def normalize_telemetry(
    raw: Mapping[str, Any],
    observed_at: datetime,
) -> TelemetrySnapshot:
    """Validate an OPC UA asset reading and create the normalized data contract."""
    if not isinstance(raw, Mapping):
        raise ValueError("raw telemetry must be a mapping")

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")

    asset_id = raw.get("assetId")
    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("assetId must be a non-empty string")

    asset = get_asset_config(asset_id)

    state = raw.get("state")
    if state not in ("RUNNING", "STOPPED"):
        raise ValueError("state must be RUNNING or STOPPED")

    temperature = _read_number(raw.get("temperature"), "temperature")
    speed = _read_number(raw.get("speed"), "speed")

    alarm = raw.get("alarm")
    if type(alarm) is not bool:
        raise ValueError("alarm must be a boolean")

    if temperature > asset.temperature_max:
        raise ValueError(
            f"temperature exceeds the maximum for asset {asset_id}"
        )

    if state == "RUNNING" and temperature < asset.temperature_min:
        raise ValueError(
            f"temperature is below the operating minimum for asset {asset_id}"
        )

    if state == "STOPPED" and temperature < STOPPED_TEMPERATURE_MIN:
        raise ValueError(
            f"temperature is below the stopped-state minimum for asset {asset_id}"
        )

    if not asset.speed_min <= speed <= asset.speed_max:
        raise ValueError(f"speed is outside the configured range for asset {asset_id}")

    if state == "STOPPED" and speed != 0.0:
        raise ValueError("speed must be zero when the asset is STOPPED")

    return TelemetrySnapshot(
        schema_version=SCHEMA_VERSION,
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        observed_at=observed_at.astimezone(timezone.utc),
        state=state,
        temperature=temperature,
        speed=speed,
        alarm=alarm,
    )
