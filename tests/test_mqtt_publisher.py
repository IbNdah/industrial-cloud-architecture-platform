"""Unit tests for the MQTT telemetry publisher."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import paho.mqtt.client as mqtt

from edge.industrial_gateway.mqtt_publisher import MqttPublisher


class TestMqttPublisher(unittest.IsolatedAsyncioTestCase):
    """Test MQTT connection and telemetry publication."""

    def setUp(self):
        self.buffer = MagicMock()
        self.mqtt_client = MagicMock()

        self.client_patch = patch(
            "edge.industrial_gateway.mqtt_publisher.mqtt.Client",
            return_value=self.mqtt_client,
        )
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)

        self.publisher = MqttPublisher(buffer=self.buffer)

    def test_connect(self):
        """Connect to the broker and start the network loop."""
        self.publisher.connect()

        self.mqtt_client.connect.assert_called_once_with(
            "127.0.0.1",
            1883,
        )
        self.mqtt_client.loop_start.assert_called_once()
        self.assertTrue(self.publisher._loop_started)

    def test_disconnect(self):
        """Disconnect from the broker and stop the network loop."""
        self.publisher.connect()
        self.publisher.disconnect()

        self.mqtt_client.disconnect.assert_called_once()
        self.mqtt_client.loop_stop.assert_called_once()
        self.assertFalse(self.publisher._loop_started)

    def test_disconnect_without_connection(self):
        """Do not disconnect when the network loop was never started."""
        self.publisher.disconnect()

        self.mqtt_client.disconnect.assert_not_called()
        self.mqtt_client.loop_stop.assert_not_called()

    def test_publish_message(self):
        """Publish a JSON payload with QoS 1 and no retention."""
        message = {
            "id": 1,
            "schema_version": "1.0",
            "asset_id": "M-101",
            "asset_type": "electric_motor",
            "observed_at": "2026-11-10T10:00:00Z",
            "state": "RUNNING",
            "temperature": 65.5,
            "speed": 1450.0,
            "alarm": False,
            "status": "PENDING",
        }

        result = MagicMock()
        result.rc = mqtt.MQTT_ERR_SUCCESS
        result.is_published.return_value = True
        self.mqtt_client.publish.return_value = result

        self.publisher._publish_message(message)

        self.mqtt_client.publish.assert_called_once()

        topic, payload = self.mqtt_client.publish.call_args.args
        options = self.mqtt_client.publish.call_args.kwargs

        self.assertEqual(
            topic,
            "industrial/assets/M-101/telemetry",
        )
        self.assertEqual(
            json.loads(payload),
            {
                "schema_version": "1.0",
                "asset_id": "M-101",
                "asset_type": "electric_motor",
                "observed_at": "2026-11-10T10:00:00Z",
                "state": "RUNNING",
                "temperature": 65.5,
                "speed": 1450.0,
                "alarm": False,
            },
        )
        self.assertEqual(options["qos"], 1)
        self.assertFalse(options["retain"])

        result.wait_for_publish.assert_called_once_with(timeout=5)
        result.is_published.assert_called_once()

    def test_publish_message_local_error(self):
        """Raise an error when Paho rejects the publish request."""
        message = {
            "asset_id": "M-101",
            "schema_version": "1.0",
            "asset_type": "electric_motor",
            "observed_at": "2026-11-10T10:00:00Z",
            "state": "RUNNING",
            "temperature": 65.5,
            "speed": 1450.0,
            "alarm": False,
        }

        result = MagicMock()
        result.rc = mqtt.MQTT_ERR_NO_CONN
        self.mqtt_client.publish.return_value = result

        with self.assertRaises(ConnectionError):
            self.publisher._publish_message(message)

        result.wait_for_publish.assert_not_called()

    def test_publish_message_timeout(self):
        """Raise an error when the broker acknowledgement is missing."""
        message = {
            "asset_id": "M-101",
            "schema_version": "1.0",
            "asset_type": "electric_motor",
            "observed_at": "2026-11-10T10:00:00Z",
            "state": "RUNNING",
            "temperature": 65.5,
            "speed": 1450.0,
            "alarm": False,
        }

        result = MagicMock()
        result.rc = mqtt.MQTT_ERR_SUCCESS
        result.is_published.return_value = False
        self.mqtt_client.publish.return_value = result

        with self.assertRaises(TimeoutError):
            self.publisher._publish_message(message)

        result.wait_for_publish.assert_called_once_with(timeout=5)
        result.is_published.assert_called_once()

    def test_publish_message_runtime_error(self):
        """Convert Paho runtime errors into connection errors."""
        message = {
            "asset_id": "M-101",
            "schema_version": "1.0",
            "asset_type": "electric_motor",
            "observed_at": "2026-11-10T10:00:00Z",
            "state": "RUNNING",
            "temperature": 65.5,
            "speed": 1450.0,
            "alarm": False,
        }

        result = MagicMock()
        result.rc = mqtt.MQTT_ERR_SUCCESS
        result.wait_for_publish.side_effect = RuntimeError("Publish failed")
        self.mqtt_client.publish.return_value = result

        with self.assertRaises(ConnectionError):
            self.publisher._publish_message(message)

    def test_publish_message_value_error(self):
        """Convert Paho queue errors into connection errors."""
        message = {
            "asset_id": "M-101",
            "schema_version": "1.0",
            "asset_type": "electric_motor",
            "observed_at": "2026-11-10T10:00:00Z",
            "state": "RUNNING",
            "temperature": 65.5,
            "speed": 1450.0,
            "alarm": False,
        }

        result = MagicMock()
        result.rc = mqtt.MQTT_ERR_SUCCESS
        result.wait_for_publish.side_effect = ValueError("Message queue is full")
        self.mqtt_client.publish.return_value = result

        with self.assertRaises(ConnectionError):
            self.publisher._publish_message(message)

    async def test_publish_pending_marks_messages_sent(self):
        """Mark messages as sent only after successful publication."""
        messages = [
            {"id": 1, "asset_id": "M-101"},
            {"id": 2, "asset_id": "P-101"},
        ]

        self.buffer.get_pending = AsyncMock(return_value=messages)
        self.buffer.mark_sent = AsyncMock()

        with patch.object(self.publisher, "_publish_message") as publish:
            published_count = await self.publisher.publish_pending()

        self.assertEqual(published_count, 2)
        self.buffer.get_pending.assert_awaited_once_with(limit=100)
        self.assertEqual(publish.call_count, 2)

        self.buffer.mark_sent.assert_any_await(1)
        self.buffer.mark_sent.assert_any_await(2)
        self.assertEqual(self.buffer.mark_sent.await_count, 2)

    async def test_publish_pending_keeps_failed_message_pending(self):
        """Do not mark a message as sent when publication fails."""
        messages = [{"id": 1, "asset_id": "M-101"}]

        self.buffer.get_pending = AsyncMock(return_value=messages)
        self.buffer.mark_sent = AsyncMock()

        with patch.object(
            self.publisher,
            "_publish_message",
            side_effect=TimeoutError("MQTT acknowledgement timeout"),
        ), self.assertRaises(TimeoutError):
            await self.publisher.publish_pending()

        self.buffer.mark_sent.assert_not_awaited()

    async def test_publish_pending_with_empty_buffer(self):
        """Return zero when no pending messages exist."""
        self.buffer.get_pending = AsyncMock(return_value=[])
        self.buffer.mark_sent = AsyncMock()

        published_count = await self.publisher.publish_pending()

        self.assertEqual(published_count, 0)
        self.buffer.mark_sent.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
