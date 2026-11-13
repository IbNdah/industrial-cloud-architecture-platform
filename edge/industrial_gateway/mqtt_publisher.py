"""Publish buffered industrial telemetry to an MQTT broker."""

import asyncio
import json
import logging

import paho.mqtt.client as mqtt

from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer

logger = logging.getLogger(__name__)

MQTT_TOPIC_TEMPLATE = "industrial/assets/{asset_id}/telemetry"
MQTT_QOS = 1
PUBLISH_TIMEOUT_SECONDS = 5


class MqttPublisher:
    """Publish pending SQLite telemetry messages to MQTT."""

    def __init__(
        self,
        buffer: SQLiteTelemetryBuffer,
        host: str = "127.0.0.1",
        port: int = 1883,
        client_id: str = "industrial-edge-gateway",
    ):
        self.buffer = buffer
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        self.host = host
        self.port = port
        self._loop_started = False

    def connect(self) -> None:
        """Connect to the MQTT broker and start its network loop."""
        self.client.connect(self.host, self.port)
        self.client.loop_start()
        self._loop_started = True

        logger.info(
            "Connected to MQTT broker at %s:%s",
            self.host,
            self.port,
        )

    def disconnect(self) -> None:
        """Stop the network loop and disconnect from the broker."""
        if not self._loop_started:
            return

        try:
            self.client.disconnect()
        finally:
            self.client.loop_stop()
            self._loop_started = False

        logger.info("Disconnected from MQTT broker")

    def _publish_message(self, message: dict) -> None:
        """Publish one message and wait for the broker acknowledgement."""
        payload = {
            key: message[key]
            for key in (
                "schema_version",
                "asset_id",
                "asset_type",
                "observed_at",
                "state",
                "temperature",
                "speed",
                "alarm",
            )
        }

        topic = MQTT_TOPIC_TEMPLATE.format(asset_id=message["asset_id"])

        result = self.client.publish(
            topic,
            json.dumps(payload),
            qos=MQTT_QOS,
            retain=False,
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(
                f"MQTT publish failed for {topic}: " f"{mqtt.error_string(result.rc)}"
            )

        try:
            result.wait_for_publish(timeout=PUBLISH_TIMEOUT_SECONDS)
        except (RuntimeError, ValueError) as exc:
            raise ConnectionError(
                f"MQTT publication failed for {topic}: {exc}"
            ) from exc

        if not result.is_published():
            raise TimeoutError(f"MQTT acknowledgement not received for {topic}")

        logger.info("Published telemetry for %s", message["asset_id"])

    async def publish_pending(self, limit: int = 100) -> int:
        """Publish pending messages and mark acknowledged messages as sent."""
        messages = await self.buffer.get_pending(limit=limit)
        published_count = 0

        for message in messages:
            await asyncio.to_thread(self._publish_message, message)
            await self.buffer.mark_sent(message["id"])
            published_count += 1

        return published_count
