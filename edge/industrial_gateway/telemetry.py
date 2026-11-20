"""Normalized telemetry contract for industrial assets."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

AssetState = Literal["RUNNING", "STOPPED"]


@dataclass(frozen=True)
class TelemetrySnapshot:
    """Validated telemetry snapshot exchanged by Edge components."""

    schema_version: str
    asset_id: str
    asset_type: str
    observed_at: datetime
    state: AssetState
    temperature: float
    speed: float
    alarm: bool
    # The ID is created once per snapshot and remains stable across delivery retries.
    message_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, str | float | bool]:
        """Serialize the snapshot using an ISO 8601 UTC timestamp."""
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")

        payload = asdict(self)
        payload["observed_at"] = (
            self.observed_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        )
        return payload
