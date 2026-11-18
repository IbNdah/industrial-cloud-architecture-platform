"""Tests for the industrial gateway lifecycle."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from edge.industrial_gateway.gateway import IndustrialGateway, main


class TestIndustrialGatewayLifecycle(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.opcua_patcher = patch(
            "edge.industrial_gateway.gateway.IndustrialOPCUAClient"
        )
        self.buffer_patcher = patch(
            "edge.industrial_gateway.gateway.SQLiteTelemetryBuffer"
        )
        self.publisher_patcher = patch("edge.industrial_gateway.gateway.MqttPublisher")

        self.mock_opcua_class = self.opcua_patcher.start()
        self.mock_buffer_class = self.buffer_patcher.start()
        self.mock_publisher_class = self.publisher_patcher.start()

        self.addCleanup(self.opcua_patcher.stop)
        self.addCleanup(self.buffer_patcher.stop)
        self.addCleanup(self.publisher_patcher.stop)

        self.gateway = IndustrialGateway()

        self.opcua = self.gateway.opcua_client
        self.buffer = self.gateway.buffer
        self.publisher = self.gateway.publisher

        self.buffer.initialize = AsyncMock()
        self.buffer.close = AsyncMock()
        self.opcua.connect = AsyncMock()
        self.opcua.disconnect = AsyncMock()
        self.publisher.connect = MagicMock()
        self.publisher.disconnect = MagicMock()

    async def test_start_initializes_and_connects_components(self):
        await self.gateway.start()

        self.buffer.initialize.assert_awaited_once()
        self.publisher.connect.assert_called_once()
        self.opcua.connect.assert_awaited_once()
        self.assertTrue(self.gateway._started)

    async def test_start_cleans_up_when_opcua_connection_fails(self):
        self.opcua.connect.side_effect = ConnectionError("OPC UA server unavailable")

        with self.assertRaises(ConnectionError):
            await self.gateway.start()

        self.buffer.initialize.assert_awaited_once()
        self.publisher.connect.assert_called_once()
        self.opcua.connect.assert_awaited_once()

        self.publisher.disconnect.assert_called_once()
        self.buffer.close.assert_awaited_once()
        self.assertFalse(self.gateway._started)

    async def test_run_stops_when_signal_file_is_created(self):
        """Stop the acquisition loop when the signal file appears."""
        self.gateway._started = True

        self.opcua.read_assets = AsyncMock(return_value=[])
        self.publisher.is_connected = True
        self.publisher.publish_pending = AsyncMock(return_value=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            self.gateway.stop_signal_path = Path(temp_dir) / "stop.signal"

            async def create_stop_signal(_):
                self.gateway.stop_signal_path.touch()

            with patch(
                "edge.industrial_gateway.gateway.asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=create_stop_signal,
            ) as mock_sleep:
                await self.gateway.run()

            self.assertTrue(self.gateway.stop_signal_path.exists())

        self.opcua.read_assets.assert_awaited_once()
        self.publisher.publish_pending.assert_awaited_once()
        mock_sleep.assert_awaited_once_with(5)

    async def test_main_stops_gateway_after_run_finishes(self):
        """Ensure main releases gateway resources after run terminates."""
        mock_gateway = MagicMock()
        mock_gateway.start = AsyncMock()
        mock_gateway.run = AsyncMock()
        mock_gateway.stop = AsyncMock()

        with patch(
            "edge.industrial_gateway.gateway.IndustrialGateway",
            return_value=mock_gateway,
        ):
            await main()

        mock_gateway.start.assert_awaited_once()
        mock_gateway.run.assert_awaited_once()
        mock_gateway.stop.assert_awaited_once()

    async def test_stop_disconnects_and_closes_components(self):
        await self.gateway.start()

        await self.gateway.stop()

        self.opcua.disconnect.assert_awaited_once()
        self.publisher.disconnect.assert_called_once()
        self.buffer.close.assert_awaited_once()
        self.assertFalse(self.gateway._started)

    async def test_run_persists_valid_telemetry(self):
        raw_snapshot = {
            "assetId": "M-101",
            "state": "RUNNING",
            "temperature": 45.0,
            "speed": 1500.0,
            "alarm": False,
        }
        normalized_snapshot = MagicMock()

        self.gateway._started = True
        self.opcua.read_assets = AsyncMock(return_value=[raw_snapshot])
        self.buffer.add = AsyncMock()
        self.publisher.is_connected = False

        with (
            patch(
                "edge.industrial_gateway.gateway.normalize_telemetry",
                return_value=normalized_snapshot,
            ) as mock_normalize,
            patch(
                "edge.industrial_gateway.gateway.asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ),
            self.assertRaises(asyncio.CancelledError),
        ):
            await self.gateway.run()

        mock_normalize.assert_called_once()
        self.buffer.add.assert_awaited_once_with(normalized_snapshot)

    async def test_run_skips_invalid_telemetry_and_continues(self):
        invalid_snapshot = {"assetId": "M-101"}
        valid_snapshot = {"assetId": "P-101"}
        normalized_snapshot = MagicMock()

        self.gateway._started = True
        self.opcua.read_assets = AsyncMock(
            return_value=[invalid_snapshot, valid_snapshot]
        )
        self.buffer.add = AsyncMock()
        self.publisher.is_connected = False

        def normalize_side_effect(raw, observed_at):
            if raw["assetId"] == "M-101":
                raise ValueError("Invalid telemetry")
            return normalized_snapshot

        with (
            patch(
                "edge.industrial_gateway.gateway.normalize_telemetry",
                side_effect=normalize_side_effect,
            ),
            patch(
                "edge.industrial_gateway.gateway.asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ),
            self.assertRaises(asyncio.CancelledError),
        ):
            await self.gateway.run()

        self.buffer.add.assert_awaited_once_with(normalized_snapshot)

    async def test_run_publishes_pending_messages_when_connected(self):
        self.gateway._started = True
        self.opcua.read_assets = AsyncMock(return_value=[])
        self.publisher.is_connected = True
        self.publisher.publish_pending = AsyncMock(return_value=2)

        with (
            patch(
                "edge.industrial_gateway.gateway.asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ),
            self.assertRaises(asyncio.CancelledError),
        ):
            await self.gateway.run()

        self.publisher.publish_pending.assert_awaited_once()

    async def test_run_reconnects_opcua_and_publishes_pending_messages(self):
        """OPC UA failure must not prevent MQTT queue delivery."""
        self.gateway._started = True

        # Simulate a lost OPC UA session.
        self.opcua.read_assets = AsyncMock(
            side_effect=ConnectionError("OPC UA connection lost")
        )
        self.opcua.reconnect = AsyncMock()

        # Pending SQLite messages remain deliverable through MQTT.
        self.publisher.is_connected = True
        self.publisher.publish_pending = AsyncMock(return_value=2)

        with (
            patch(
                "edge.industrial_gateway.gateway.asyncio.sleep",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError,
            ),
            self.assertRaises(asyncio.CancelledError),
        ):
            await self.gateway.run()

        self.opcua.reconnect.assert_awaited_once()
        self.publisher.publish_pending.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
