"""Data models for industrial asset telemetry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

AssetState = Literal["RUNNING", "STOPPED"]


@dataclass(frozen=True)
class AssetConfig:
    """Static configuration of an industrial asset."""

    asset_id: str
    asset_type: str
    temperature_min: float
    temperature_max: float
    speed_min: float
    speed_max: float
    alarm_temperature: float


@dataclass(frozen=True)
class Telemetry:
    """Telemetry snapshot generated for an industrial asset."""

    asset_id: str
    asset_type: str
    timestamp: datetime
    state: AssetState
    temperature: float
    speed: float
    alarm: bool
