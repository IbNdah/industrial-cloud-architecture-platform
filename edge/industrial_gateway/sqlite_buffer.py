"""Persistent SQLite buffer for validated industrial telemetry."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from edge.industrial_gateway.telemetry import TelemetrySnapshot


class SQLiteTelemetryBuffer:
    """Persist telemetry locally until its MQTT delivery is confirmed."""

    def __init__(self, database_path: str | Path = "data/edge_buffer.db") -> None:
        self.database_path = Path(database_path)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create the database directory, open SQLite and ensure the table exists."""
        if self._connection is not None:
            return

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.database_path)
        self._connection.row_factory = aiosqlite.Row

        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.execute("PRAGMA busy_timeout = 5000")
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_version TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('RUNNING', 'STOPPED')),
                temperature REAL NOT NULL,
                speed REAL NOT NULL,
                alarm INTEGER NOT NULL CHECK (alarm IN (0, 1)),
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'SENT')),
                created_at TEXT NOT NULL
            )
            """
        )
        await self._connection.commit()

    async def add(self, snapshot: TelemetrySnapshot) -> int:
        """Persist one validated snapshot and return its local database identifier."""
        connection = self._require_connection()
        payload = snapshot.to_dict()
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        cursor = await connection.execute(
            """
            INSERT INTO telemetry_buffer (
                schema_version, asset_id, asset_type, observed_at,
                state, temperature, speed, alarm, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            (
                payload["schema_version"],
                payload["asset_id"],
                payload["asset_type"],
                payload["observed_at"],
                payload["state"],
                payload["temperature"],
                payload["speed"],
                int(payload["alarm"]),
                created_at,
            ),
        )
        await connection.commit()
        return int(cursor.lastrowid)

    async def get_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return pending messages in insertion order, oldest first."""
        connection = self._require_connection()
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")

        cursor = await connection.execute(
            """
            SELECT id, schema_version, asset_id, asset_type, observed_at,
                   state, temperature, speed, alarm, status, created_at
            FROM telemetry_buffer
            WHERE status = 'PENDING'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()

        return [
            {**dict(row), "alarm": bool(row["alarm"])}
            for row in rows
        ]

    async def mark_sent(self, message_id: int) -> bool:
        """Mark a buffered message as sent; return whether a row was updated."""
        connection = self._require_connection()
        if isinstance(message_id, bool) or not isinstance(message_id, int) or message_id < 1:
            raise ValueError("message_id must be a positive integer")

        cursor = await connection.execute(
            """
            UPDATE telemetry_buffer
            SET status = 'SENT'
            WHERE id = ? AND status = 'PENDING'
            """,
            (message_id,),
        )
        await connection.commit()
        return cursor.rowcount == 1

    async def close(self) -> None:
        """Close the database connection safely."""
        if self._connection is None:
            return

        connection = self._connection
        self._connection = None
        await connection.close()

    def _require_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("SQLite buffer is not initialized")
        return self._connection

    async def __aenter__(self) -> "SQLiteTelemetryBuffer":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.close()
