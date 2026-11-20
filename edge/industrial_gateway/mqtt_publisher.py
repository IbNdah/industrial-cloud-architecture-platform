"""Publish buffered industrial telemetry to an MQTT broker."""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import ssl
import time
from urllib.parse import quote

import paho.mqtt.client as mqtt

from edge.industrial_gateway.config import GatewayConfig
from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer

logger = logging.getLogger(__name__)

MQTT_QOS = 1


class MqttPublisher:
    """Publish pending SQLite telemetry messages to MQTT."""

    def __init__(
        self,
        buffer: SQLiteTelemetryBuffer,
        config: GatewayConfig | None = None,
        host: str | None = None,
        port: int | None = None,
        client_id: str | None = None,
    ) -> None:
        self.buffer = buffer
        self.config = config or GatewayConfig()

        # Allow explicit connection parameters for local MQTT tests.
        self.host = host if host is not None else self.config.effective_host
        self.port = port if port is not None else self.config.effective_port
        effective_client_id = (
            client_id if client_id is not None else self.config.effective_client_id
        )

        self._connect_timeout = self.config.connect_timeout
        self._publish_timeout = self.config.publish_timeout

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=effective_client_id,
            protocol=mqtt.MQTTv311,
        )

        # Track the network loop and broker connection separately.
        self._loop_started = False
        self._connected = False
        self._disconnecting = False

        self.client.enable_logger(logger)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)

        # IoT Hub requires an encrypted MQTT connection.
        if self.config.transport == "azure_iot_hub":
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
            self.client.tls_insecure_set(False)

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

        self._disconnecting = False

        if self.config.transport == "azure_iot_hub":
            self._configure_azure_auth()

        # Paho handles connection retries when the broker is unavailable.
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
        deadline = loop.time() + self._connect_timeout

        while not self._connected:
            if loop.time() >= deadline:
                raise TimeoutError(
                    "MQTT broker connection was not established "
                    f"within {self._connect_timeout} seconds"
                )

            await asyncio.sleep(0.1)

    def _publish_message(self, message: dict) -> None:
        """Publish one message and wait for the broker acknowledgement."""

        # Keep the published payload aligned with telemetry schema 1.1.
        payload = {
            key: message[key]
            for key in (
                "schema_version",
                "message_id",
                "asset_id",
                "asset_type",
                "observed_at",
                "state",
                "temperature",
                "speed",
                "alarm",
            )
        }

        topic = self.config.get_telemetry_topic(message["asset_id"])

        result = self.client.publish(
            topic,
            json.dumps(payload),
            qos=MQTT_QOS,
            retain=False,
        )

        # Reject immediate errors before waiting for PUBACK.
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(
                f"MQTT publish failed for {topic}: " f"{mqtt.error_string(result.rc)}"
            )

        try:
            result.wait_for_publish(timeout=self._publish_timeout)
        except (RuntimeError, ValueError) as exc:
            raise ConnectionError(
                f"MQTT publication failed for {topic}: {exc}"
            ) from exc

        # Keep the message in SQLite until QoS 1 acknowledgement arrives.
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

            # Mark only acknowledged messages as sent.
            await self.buffer.mark_sent(message["id"])
            published_count += 1

        return published_count

    def _configure_azure_auth(self) -> None:
        """Generate and configure an IoT Hub SAS authentication token."""
        resource_uri = (
            f"{self.config.iot_hub_hostname}/devices/"
            f"{self.config.iot_hub_device_id}"
        )

        encoded_uri = quote(resource_uri, safe="")
        expiry = str(int(time.time()) + self.config.sas_token_ttl_seconds)

        # Sign the encoded resource URI and expiration timestamp.
        signing_key = base64.b64decode(self.config.iot_hub_device_key)

        signature = hmac.new(
            signing_key,
            f"{encoded_uri}\n{expiry}".encode(),
            hashlib.sha256,
        ).digest()

        encoded_signature = quote(
            base64.b64encode(signature).decode("utf-8"),
            safe="",
        )

        sas_token = (
            f"SharedAccessSignature sr={encoded_uri}"
            f"&sig={encoded_signature}&se={expiry}"
        )

        self.client.username_pw_set(
            username=self.config.iot_hub_username,
            password=sas_token,
        )
