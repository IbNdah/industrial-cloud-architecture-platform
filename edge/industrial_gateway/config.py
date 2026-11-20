import os
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import quote

TransportType = Literal["local_mqtt", "azure_iot_hub"]

IOTHUB_API_VERSION = "2021-04-12"


@dataclass(frozen=True)
class GatewayConfig:
    transport: TransportType = "local_mqtt"

    # Local MQTT broker settings
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    mqtt_client_id: str = "industrial-edge-gateway"
    mqtt_keepalive: int = 60
    mqtt_topic_template: str = "industrial/assets/{asset_id}/telemetry"

    # Azure IoT Hub settings
    iot_hub_hostname: str | None = None
    iot_hub_device_id: str | None = None
    iot_hub_device_key: str | None = field(default=None, repr=False)
    sas_token_ttl_seconds: int = 3600

    # Connection and publishing timeouts
    connect_timeout: int = 10
    publish_timeout: int = 5

    def __post_init__(self) -> None:
        if self.transport not in ("local_mqtt", "azure_iot_hub"):
            raise ValueError(f"Unsupported transport: {self.transport}")

        if self.transport == "local_mqtt":
            if not 1 <= self.mqtt_port <= 65535:
                raise ValueError(
                    f"mqtt_port must be between 1 and 65535: {self.mqtt_port}"
                )

        if self.mqtt_keepalive <= 0:
            raise ValueError("mqtt_keepalive must be positive")

        if self.connect_timeout <= 0 or self.publish_timeout <= 0:
            raise ValueError("Connection and publish timeouts must be positive")

        if self.sas_token_ttl_seconds <= 0:
            raise ValueError("sas_token_ttl_seconds must be positive")

        if self.transport == "local_mqtt":
            if not self.mqtt_host.strip():
                raise ValueError("mqtt_host cannot be empty")

            if "{asset_id}" not in self.mqtt_topic_template:
                raise ValueError(
                    "mqtt_topic_template must contain the {asset_id} placeholder"
                )

        if self.transport == "azure_iot_hub":
            if not self.iot_hub_hostname:
                raise ValueError("IOTHUB_HOSTNAME is required")

            if not self.iot_hub_device_id:
                raise ValueError("IOTHUB_DEVICE_ID is required")

            if not self.iot_hub_device_key:
                raise ValueError("IOTHUB_DEVICE_KEY is required")

            if "://" in self.iot_hub_hostname or "/" in self.iot_hub_hostname:
                raise ValueError("iot_hub_hostname must contain only the hostname")

    @property
    def effective_host(self) -> str:
        if self.transport == "azure_iot_hub":
            return self.iot_hub_hostname or ""

        return self.mqtt_host

    @property
    def effective_port(self) -> int:
        if self.transport == "azure_iot_hub":
            return 8883

        return self.mqtt_port

    def get_telemetry_topic(self, asset_id: str) -> str:
        if not asset_id.strip():
            raise ValueError("asset_id cannot be empty")

        if self.transport == "azure_iot_hub":
            device_id = quote(self.iot_hub_device_id or "", safe="")
            return f"devices/{device_id}/messages/events/"

        return self.mqtt_topic_template.format(asset_id=asset_id)

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        transport = os.getenv("GATEWAY_TRANSPORT", "local_mqtt")

        return cls(
            transport=transport,
            mqtt_host=os.getenv("MQTT_HOST", "127.0.0.1"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "industrial-edge-gateway"),
            mqtt_keepalive=int(os.getenv("MQTT_KEEPALIVE", "60")),
            mqtt_topic_template=os.getenv(
                "MQTT_TOPIC_TEMPLATE",
                "industrial/assets/{asset_id}/telemetry",
            ),
            iot_hub_hostname=os.getenv("IOTHUB_HOSTNAME"),
            iot_hub_device_id=os.getenv("IOTHUB_DEVICE_ID"),
            iot_hub_device_key=os.getenv("IOTHUB_DEVICE_KEY"),
            sas_token_ttl_seconds=int(
                os.getenv("IOTHUB_SAS_TOKEN_TTL_SECONDS", "3600")
            ),
            connect_timeout=int(os.getenv("MQTT_CONNECT_TIMEOUT", "10")),
            publish_timeout=int(os.getenv("MQTT_PUBLISH_TIMEOUT", "5")),
        )

    @property
    def effective_client_id(self) -> str:
        if self.transport == "azure_iot_hub":
            return self.iot_hub_device_id or ""

        return self.mqtt_client_id

    @property
    def iot_hub_username(self) -> str:
        if self.transport != "azure_iot_hub":
            raise ValueError("IoT Hub username is only available for Azure")

        hostname = self.iot_hub_hostname or ""
        device_id = quote(self.iot_hub_device_id or "", safe="")

        return f"{hostname}/{device_id}/" f"?api-version={IOTHUB_API_VERSION}"

    @property
    def iot_hub_telemetry_topic(self) -> str:
        if self.transport != "azure_iot_hub":
            raise ValueError("IoT Hub topic is only available for Azure")

        device_id = quote(self.iot_hub_device_id or "", safe="")
        return f"devices/{device_id}/messages/events/"
