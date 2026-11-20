"""Integration test for the industrial Gateway and MQTT delivery."""

import asyncio
import json
import queue
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path

import paho.mqtt.client as mqtt
from asyncua import Server

from edge.industrial_gateway.gateway import IndustrialGateway
from simulator.industrial_assets.opcua_server import (
    NAMESPACE_URI,
    build_address_space,
    update_telemetry,
)
from simulator.industrial_assets.simulator import IndustrialSimulator

OPCUA_ENDPOINT = "opc.tcp://127.0.0.1:4851/industrial/"
MOSQUITTO_EXECUTABLE = r"C:\Program Files\mosquitto\mosquitto.exe"
EXPECTED_ASSETS = {"M-101", "M-102", "P-101", "C-101", "F-101"}


def get_free_port() -> int:
    """Return an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestGatewayMqttIntegration(unittest.IsolatedAsyncioTestCase):
    """Verify OPC UA acquisition, SQLite persistence and MQTT delivery."""

    async def test_gateway_publishes_all_assets_to_mqtt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)
            mqtt_port = get_free_port()
            database_path = test_path / "gateway.db"
            config_path = test_path / "mosquitto.conf"

            config_path.write_text(
                f"listener {mqtt_port} 127.0.0.1\n"
                "allow_anonymous true\n"
                "persistence false\n"
                "log_type error\n",
                encoding="utf-8",
            )

            broker = subprocess.Popen(
                [
                    MOSQUITTO_EXECUTABLE,
                    "-c",
                    str(config_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            subscriber = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id="gateway-integration-test",
            )
            received_messages = queue.Queue()
            subscribed = asyncio.Event()
            connected = asyncio.Event()

            def on_connect(client, userdata, connect_flags, reason_code, properties):
                if not reason_code.is_failure:
                    connected_loop.call_soon_threadsafe(connected.set)
                    client.subscribe("industrial/assets/+/telemetry", qos=1)

            def on_subscribe(client, userdata, mid, reason_code_list, properties):
                connected_loop.call_soon_threadsafe(subscribed.set)

            def on_message(client, userdata, message):
                received_messages.put((message.topic, json.loads(message.payload)))

            subscriber.on_connect = on_connect
            subscriber.on_subscribe = on_subscribe
            subscriber.on_message = on_message

            gateway = None
            run_task = None
            connected_loop = asyncio.get_running_loop()

            try:
                # Wait until the temporary broker accepts TCP connections.
                deadline = time.monotonic() + 10

                while time.monotonic() < deadline:
                    if broker.poll() is not None:
                        self.fail("Mosquitto process exited unexpectedly")

                    try:
                        with socket.create_connection(
                            ("127.0.0.1", mqtt_port), timeout=0.2
                        ):
                            break
                    except OSError:
                        await asyncio.sleep(0.1)
                else:
                    self.fail("Mosquitto broker did not start")

                subscriber.connect("127.0.0.1", mqtt_port)
                subscriber.loop_start()

                await asyncio.wait_for(connected.wait(), timeout=10)
                await asyncio.wait_for(subscribed.wait(), timeout=10)

                server = Server()
                await server.init()
                server.set_endpoint(OPCUA_ENDPOINT)
                await server.set_application_uri(NAMESPACE_URI)
                asset_nodes = await build_address_space(server)

                async with server:
                    await update_telemetry(
                        asset_nodes,
                        IndustrialSimulator(seed=42),
                    )

                    gateway = IndustrialGateway(
                        opcua_endpoint=OPCUA_ENDPOINT,
                        mqtt_host="127.0.0.1",
                        mqtt_port=mqtt_port,
                        database_path=str(database_path),
                    )
                    gateway.stop_signal_path = test_path / "gateway.stop"

                    await gateway.start()
                    run_task = asyncio.create_task(gateway.run())

                    # Wait for one message from each configured asset.
                    messages = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._collect_messages,
                            received_messages,
                            len(EXPECTED_ASSETS),
                        ),
                        timeout=20,
                    )

                    received_assets = set()

                    for topic, payload in messages:
                        asset_id = payload["asset_id"]
                        received_assets.add(asset_id)

                        self.assertEqual(
                            topic,
                            f"industrial/assets/{asset_id}/telemetry",
                        )
                        self.assertEqual(payload["schema_version"], "1.1")
                        self.assertIsInstance(payload["message_id"], str)
                        self.assertEqual(payload["asset_id"], asset_id)
                        self.assertIn(payload["state"], {"RUNNING", "STOPPED"})
                        self.assertIsInstance(payload["temperature"], float)
                        self.assertIsInstance(payload["speed"], float)
                        self.assertIsInstance(payload["alarm"], bool)
                        self.assertTrue(payload["observed_at"].endswith("Z"))

                    self.assertEqual(received_assets, EXPECTED_ASSETS)

                    gateway.stop_signal_path.touch()
                    await asyncio.wait_for(run_task, timeout=7)
                    await gateway.stop()

                with closing(sqlite3.connect(database_path)) as connection:
                    rows = connection.execute("""
                        SELECT asset_id, status, COUNT(*)
                        FROM telemetry_buffer
                        GROUP BY asset_id, status
                        """).fetchall()

                self.assertTrue(rows)

                for asset_id in EXPECTED_ASSETS:
                    asset_rows = [row for row in rows if row[0] == asset_id]
                    self.assertTrue(asset_rows)
                    self.assertTrue(all(row[1] == "SENT" for row in asset_rows))

            finally:
                if run_task is not None and not run_task.done():
                    gateway.stop_signal_path.touch()
                    await asyncio.wait_for(run_task, timeout=7)

                if gateway is not None:
                    await gateway.stop()

                subscriber.disconnect()
                subscriber.loop_stop()

                broker.terminate()
                try:
                    broker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    broker.kill()
                    broker.wait()

    @staticmethod
    def _collect_messages(message_queue, expected_count):
        """Collect the first message received for each expected asset."""
        messages_by_asset = {}

        deadline = time.monotonic() + 18

        while len(messages_by_asset) < expected_count:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                break

            try:
                topic, payload = message_queue.get(timeout=remaining)
            except queue.Empty:
                break

            messages_by_asset[payload["asset_id"]] = (topic, payload)

        if len(messages_by_asset) != expected_count:
            raise AssertionError(
                f"Expected {expected_count} assets, "
                f"received {len(messages_by_asset)}"
            )

        return list(messages_by_asset.values())


if __name__ == "__main__":
    unittest.main()
