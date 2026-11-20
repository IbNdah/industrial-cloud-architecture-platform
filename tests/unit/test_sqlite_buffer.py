"""Unit tests for the SQLite telemetry buffer."""

import sqlite3
import tempfile
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path

from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer
from edge.industrial_gateway.telemetry import TelemetrySnapshot


class SQLiteTelemetryBufferTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "edge_buffer.db"
        self.snapshot = TelemetrySnapshot(
            schema_version="1.1",
            asset_id="M-101",
            asset_type="electric_motor",
            observed_at=datetime(2026, 11, 10, 8, 30, tzinfo=UTC),
            state="RUNNING",
            temperature=52.5,
            speed=1200.0,
            alarm=False,
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    async def test_add_stores_snapshot_as_pending(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            buffer_id = await buffer.add(self.snapshot)
            pending = await buffer.get_pending()

        self.assertGreater(buffer_id, 0)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], buffer_id)
        self.assertEqual(pending[0]["message_id"], self.snapshot.message_id)
        self.assertEqual(pending[0]["asset_id"], "M-101")
        self.assertEqual(pending[0]["asset_type"], "electric_motor")
        self.assertEqual(pending[0]["temperature"], 52.5)
        self.assertEqual(pending[0]["speed"], 1200.0)
        self.assertIs(pending[0]["alarm"], False)
        self.assertEqual(pending[0]["status"], "PENDING")

    async def test_pending_messages_are_returned_in_insertion_order(self) -> None:
        second_snapshot = TelemetrySnapshot(
            schema_version="1.1",
            asset_id="P-101",
            asset_type="pump",
            observed_at=self.snapshot.observed_at,
            state="RUNNING",
            temperature=45.0,
            speed=2500.0,
            alarm=False,
        )

        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            first_id = await buffer.add(self.snapshot)
            second_id = await buffer.add(second_snapshot)
            pending = await buffer.get_pending()

        self.assertEqual(
            [message["id"] for message in pending],
            [first_id, second_id],
        )

    async def test_mark_sent_removes_message_from_pending_results(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            buffer_id = await buffer.add(self.snapshot)
            updated = await buffer.mark_sent(buffer_id)
            pending = await buffer.get_pending()

        self.assertTrue(updated)
        self.assertEqual(pending, [])

    async def test_mark_sent_returns_false_for_unknown_or_already_sent_id(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            buffer_id = await buffer.add(self.snapshot)

            self.assertFalse(await buffer.mark_sent(9999))
            self.assertTrue(await buffer.mark_sent(buffer_id))
            self.assertFalse(await buffer.mark_sent(buffer_id))

    async def test_pending_messages_survive_connection_restart(self) -> None:
        first_buffer = SQLiteTelemetryBuffer(self.database_path)
        await first_buffer.initialize()
        buffer_id = await first_buffer.add(self.snapshot)
        await first_buffer.close()

        second_buffer = SQLiteTelemetryBuffer(self.database_path)
        await second_buffer.initialize()
        pending = await second_buffer.get_pending()
        await second_buffer.close()

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], buffer_id)
        self.assertEqual(pending[0]["message_id"], self.snapshot.message_id)
        self.assertEqual(pending[0]["asset_id"], "M-101")

    async def test_get_pending_respects_limit(self) -> None:
        second_snapshot = TelemetrySnapshot(
            schema_version="1.1",
            asset_id="M-102",
            asset_type="electric_motor",
            observed_at=self.snapshot.observed_at,
            state="RUNNING",
            temperature=48.0,
            speed=1100.0,
            alarm=False,
        )

        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            first_buffer_id = await buffer.add(self.snapshot)
            second_buffer_id = await buffer.add(second_snapshot)
            pending = await buffer.get_pending(limit=1)

        self.assertNotEqual(first_buffer_id, second_buffer_id)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], first_buffer_id)
        self.assertEqual(pending[0]["message_id"], self.snapshot.message_id)

    async def test_initialize_migrates_legacy_database(self) -> None:
        connection = sqlite3.connect(self.database_path)

        try:
            connection.execute("""
                CREATE TABLE telemetry_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema_version TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    speed REAL NOT NULL,
                    alarm INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL
                )
                """)

            connection.execute(
                """
                INSERT INTO telemetry_buffer (
                    schema_version, asset_id, asset_type, observed_at,
                    state, temperature, speed, alarm, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "1.0",
                    "M-101",
                    "electric_motor",
                    "2026-11-10T08:30:00Z",
                    "RUNNING",
                    52.5,
                    1200.0,
                    0,
                    "PENDING",
                    "2026-11-10T08:30:00Z",
                ),
            )

            connection.commit()

        finally:
            # Release the database fil beforethe asynchronous migration
            connection.close()

        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            pending = await buffer.get_pending()

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], 1)
        self.assertEqual(pending[0]["asset_id"], "M-101")
        self.assertTrue(pending[0]["message_id"])

        # Verify that the migration generated a valid UUID.
        uuid.UUID(pending[0]["message_id"])


if __name__ == "__main__":
    unittest.main()
