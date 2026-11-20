import os
from unittest.mock import patch

import pytest

from edge.industrial_gateway.config import GatewayConfig


def test_default_configuration_uses_local_mqtt():
    config = GatewayConfig()

    assert config.transport == "local_mqtt"
    assert config.mqtt_host == "127.0.0.1"
    assert config.mqtt_port == 1883
    assert config.effective_client_id == "industrial-edge-gateway"


def test_configuration_is_immutable():
    config = GatewayConfig()

    with pytest.raises(AttributeError):
        config.mqtt_port = 8883


def test_azure_configuration_derives_connection_parameters():
    config = GatewayConfig(
        transport="azure_iot_hub",
        iot_hub_hostname="test.azure-devices.net",
        iot_hub_device_id="edge-gateway-01",
        iot_hub_device_key="test-secret",
    )

    assert config.effective_client_id == "edge-gateway-01"
    assert config.iot_hub_username == (
        "test.azure-devices.net/edge-gateway-01/" "?api-version=2021-04-12"
    )
    assert config.iot_hub_telemetry_topic == (
        "devices/edge-gateway-01/messages/events/"
    )


def test_device_key_is_hidden_from_object_representation():
    config = GatewayConfig(
        transport="azure_iot_hub",
        iot_hub_hostname="test.azure-devices.net",
        iot_hub_device_id="edge-gateway-01",
        iot_hub_device_key="test-secret",
    )

    assert "test-secret" not in repr(config)


def test_unknown_transport_is_rejected():
    with pytest.raises(ValueError, match="Unsupported transport"):
        GatewayConfig(transport="unknown")


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_invalid_mqtt_port_is_rejected(port):
    with pytest.raises(ValueError, match="mqtt_port"):
        GatewayConfig(mqtt_port=port)


def test_empty_local_host_is_rejected():
    with pytest.raises(ValueError, match="mqtt_host"):
        GatewayConfig(mqtt_host=" ")


def test_invalid_local_topic_template_is_rejected():
    with pytest.raises(ValueError, match="asset_id"):
        GatewayConfig(mqtt_topic_template="industrial/telemetry")


@pytest.mark.parametrize(
    "parameters",
    [
        {"mqtt_keepalive": 0},
        {"connect_timeout": 0},
        {"publish_timeout": -1},
        {"sas_token_ttl_seconds": 0},
    ],
)
def test_non_positive_timeouts_are_rejected(parameters):
    with pytest.raises(ValueError):
        GatewayConfig(**parameters)


@pytest.mark.parametrize(
    ("field", "error_message"),
    [
        ("iot_hub_hostname", "IOTHUB_HOSTNAME"),
        ("iot_hub_device_id", "IOTHUB_DEVICE_ID"),
        ("iot_hub_device_key", "IOTHUB_DEVICE_KEY"),
    ],
)
def test_azure_requires_connection_credentials(field, error_message):
    parameters = {
        "transport": "azure_iot_hub",
        "iot_hub_hostname": "test.azure-devices.net",
        "iot_hub_device_id": "edge-gateway-01",
        "iot_hub_device_key": "test-secret",
    }
    parameters[field] = None

    with pytest.raises(ValueError, match=error_message):
        GatewayConfig(**parameters)


def test_invalid_azure_hostname_is_rejected():
    with pytest.raises(ValueError, match="iot_hub_hostname"):
        GatewayConfig(
            transport="azure_iot_hub",
            iot_hub_hostname="https://test.azure-devices.net",
            iot_hub_device_id="edge-gateway-01",
            iot_hub_device_key="test-secret",
        )


def test_from_env_loads_local_configuration():
    environment = {
        "GATEWAY_TRANSPORT": "local_mqtt",
        "MQTT_HOST": "192.168.1.10",
        "MQTT_PORT": "1884",
        "MQTT_CLIENT_ID": "test-gateway",
        "MQTT_KEEPALIVE": "45",
    }

    with patch.dict(os.environ, environment, clear=True):
        config = GatewayConfig.from_env()

    assert config.transport == "local_mqtt"
    assert config.mqtt_host == "192.168.1.10"
    assert config.mqtt_port == 1884
    assert config.mqtt_client_id == "test-gateway"
    assert config.mqtt_keepalive == 45


def test_from_env_loads_azure_configuration():
    environment = {
        "GATEWAY_TRANSPORT": "azure_iot_hub",
        "IOTHUB_HOSTNAME": "test.azure-devices.net",
        "IOTHUB_DEVICE_ID": "edge-gateway-01",
        "IOTHUB_DEVICE_KEY": "test-secret",
    }

    with patch.dict(os.environ, environment, clear=True):
        config = GatewayConfig.from_env()

    assert config.transport == "azure_iot_hub"
    assert config.iot_hub_device_id == "edge-gateway-01"
    assert config.iot_hub_device_key == "test-secret"


def test_invalid_environment_port_conversion_is_rejected():
    environment = {"MQTT_PORT": "invalid"}

    with patch.dict(os.environ, environment, clear=True), pytest.raises(ValueError):
        GatewayConfig.from_env()


def test_azure_properties_are_unavailable_for_local_transport():
    config = GatewayConfig()

    with pytest.raises(ValueError, match="Azure"):
        _ = config.iot_hub_username

    with pytest.raises(ValueError, match="Azure"):
        _ = config.iot_hub_telemetry_topic
