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
CONNECTION_TIMEOUT_SECONDS = 15


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

        # Track network loop and broker connection separately.
        self._loop_started = False
        self._connected = False
        self._disconnecting = False

        # Register callbacks and configure automatic reconnection.
        self.client.enable_logger(logger)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)

    @property
    def is_connected(self) -> bool:
        """Return whether the broker connection has been confirmed."""
        return self._connected

    def _on_connect(
        self,
        client,
        userdata,
        connect_flags,
        reason_code,
        properties,
    ) -> None:
        """Update connection state after receiving CONNACK."""
        self._connected = not reason_code.is_failure

        if self._connected:
            logger.info("MQTT connection established")
        else:
            logger.error("MQTT connection rejected: %s", reason_code)

    def _on_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:
        """Update connection state after MQTT disconnection."""
        self._connected = False

        if self._disconnecting:
            logger.info("MQTT connection intentionally closed")
        else:
            logger.warning("MQTT connection lost: %s", reason_code)

    def connect(self) -> None:
        """Start asynchronous connection attempts and the network loop."""
        if self._loop_started:
            return

        # Let Paho retry even when the broker is initially unavailable.
        self.client.connect_async(self.host, self.port)
        self.client.loop_start()
        self._loop_started = True

        logger.info(
            "MQTT connection attempts started for %s:%s",
            self.host,
            self.port,
        )

    def disconnect(self) -> None:
        """Stop the network loop and disconnect from the broker."""
        if not self._loop_started:
            return

        self._disconnecting = True

        try:
            self.client.disconnect()
        finally:
            self.client.loop_stop()
            self._loop_started = False
            self._connected = False

        logger.info("MQTT publisher stopped")

    async def _wait_until_connected(self) -> None:
        """Wait until the broker confirms the connection."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CONNECTION_TIMEOUT_SECONDS

        while not self._connected:
            if loop.time() >= deadline:
                raise TimeoutError(
                    "MQTT broker connection was not established "
                    f"within {CONNECTION_TIMEOUT_SECONDS} seconds"
                )

            await asyncio.sleep(0.1)

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

        # Reject immediate publication errors before waiting for PUBACK.
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

        # QoS 1 requires broker acknowledgement before marking data as sent.
        if not result.is_published():
            raise TimeoutError(f"MQTT acknowledgement not received for {topic}")

        logger.info("Published telemetry for %s", message["asset_id"])

    async def publish_pending(self, limit: int = 100) -> int:
        """Publish pending messages and mark acknowledged messages as sent."""
        messages = await self.buffer.get_pending(limit=limit)

        if not messages:
            return 0

        await self._wait_until_connected()

        published_count = 0

        for message in messages:
            await asyncio.to_thread(self._publish_message, message)
            await self.buffer.mark_sent(message["id"])
            published_count += 1

        return published_count
