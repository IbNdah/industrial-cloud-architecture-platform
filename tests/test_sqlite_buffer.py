"""Unit tests for the SQLite telemetry buffer."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer
from edge.industrial_gateway.telemetry import TelemetrySnapshot


class SQLiteTelemetryBufferTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "edge_buffer.db"
        self.snapshot = TelemetrySnapshot(
            schema_version="1.0",
            asset_id="M-101",
            asset_type="electric_motor",
            observed_at=datetime(2026, 11, 10, 8, 30, tzinfo=timezone.utc),
            state="RUNNING",
            temperature=52.5,
            speed=1200.0,
            alarm=False,
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    async def test_add_stores_snapshot_as_pending(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            message_id = await buffer.add(self.snapshot)
            pending = await buffer.get_pending()

        self.assertGreater(message_id, 0)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], message_id)
        self.assertEqual(pending[0]["asset_id"], "M-101")
        self.assertEqual(pending[0]["asset_type"], "electric_motor")
        self.assertEqual(pending[0]["temperature"], 52.5)
        self.assertEqual(pending[0]["speed"], 1200.0)
        self.assertIs(pending[0]["alarm"], False)
        self.assertEqual(pending[0]["status"], "PENDING")

    async def test_pending_messages_are_returned_in_insertion_order(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            first_id = await buffer.add(self.snapshot)
            second_snapshot = TelemetrySnapshot(
                schema_version="1.0",
                asset_id="P-101",
                asset_type="pump",
                observed_at=self.snapshot.observed_at,
                state="RUNNING",
                temperature=45.0,
                speed=2500.0,
                alarm=False,
            )
            second_id = await buffer.add(second_snapshot)
            pending = await buffer.get_pending()

        self.assertEqual(
            [message["id"] for message in pending],
            [first_id, second_id],
        )

    async def test_mark_sent_removes_message_from_pending_results(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            message_id = await buffer.add(self.snapshot)

            updated = await buffer.mark_sent(message_id)
            pending = await buffer.get_pending()

        self.assertTrue(updated)
        self.assertEqual(pending, [])

    async def test_mark_sent_returns_false_for_unknown_or_already_sent_id(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            message_id = await buffer.add(self.snapshot)

            self.assertFalse(await buffer.mark_sent(9999))
            self.assertTrue(await buffer.mark_sent(message_id))
            self.assertFalse(await buffer.mark_sent(message_id))

    async def test_pending_messages_survive_connection_restart(self) -> None:
        first_buffer = SQLiteTelemetryBuffer(self.database_path)
        await first_buffer.initialize()
        message_id = await first_buffer.add(self.snapshot)
        await first_buffer.close()

        second_buffer = SQLiteTelemetryBuffer(self.database_path)
        await second_buffer.initialize()
        pending = await second_buffer.get_pending()
        await second_buffer.close()

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], message_id)
        self.assertEqual(pending[0]["asset_id"], "M-101")

    async def test_get_pending_respects_limit(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            await buffer.add(self.snapshot)
            await buffer.add(self.snapshot)
            pending = await buffer.get_pending(limit=1)

        self.assertEqual(len(pending), 1)

    async def test_get_pending_rejects_invalid_limit(self) -> None:
        async with SQLiteTelemetryBuffer(self.database_path) as buffer:
            for invalid_limit in (0, -1, True, 1.5):
                with self.subTest(limit=invalid_limit):
                    with self.assertRaisesRegex(ValueError, "limit must be"):
                        await buffer.get_pending(limit=invalid_limit)

    async def test_operations_require_initialization(self) -> None:
        buffer = SQLiteTelemetryBuffer(self.database_path)

        with self.assertRaisesRegex(RuntimeError, "not initialized"):
            await buffer.add(self.snapshot)

        with self.assertRaisesRegex(RuntimeError, "not initialized"):
            await buffer.get_pending()

        with self.assertRaisesRegex(RuntimeError, "not initialized"):
            await buffer.mark_sent(1)

    async def test_close_is_safe_when_not_initialized(self) -> None:
        buffer = SQLiteTelemetryBuffer(self.database_path)
        await buffer.close()


if __name__ == "__main__":
    unittest.main()
