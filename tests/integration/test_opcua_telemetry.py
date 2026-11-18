"""Integration tests for OPC UA telemetry updates."""

import unittest

from asyncua import Server

from edge.industrial_gateway.opcua_client import IndustrialOPCUAClient
from simulator.industrial_assets.opcua_server import (
    NAMESPACE_URI,
    build_address_space,
    update_telemetry,
)
from simulator.industrial_assets.simulator import (
    ASSETS,
    IndustrialSimulator,
)

TEST_ENDPOINT = "opc.tcp://127.0.0.1:4850/industrial/"


class TestOpcUaTelemetryIntegration(unittest.IsolatedAsyncioTestCase):
    """Verify telemetry updates through a real OPC UA connection."""

    async def test_simulated_telemetry_is_available_to_opcua_client(self):
        server = Server()
        await server.init()
        server.set_endpoint(TEST_ENDPOINT)
        await server.set_application_uri(NAMESPACE_URI)

        asset_nodes = await build_address_space(server)

        simulator = IndustrialSimulator(seed=42)
        expected_simulator = IndustrialSimulator(seed=42)

        expected_measurements = {
            asset.asset_id: expected_simulator.generate_telemetry(asset)
            for asset in ASSETS
        }

        async with server:
            await update_telemetry(asset_nodes, simulator)

            async with IndustrialOPCUAClient(TEST_ENDPOINT) as client:
                snapshots = await client.read_assets()

        self.assertEqual(len(snapshots), len(ASSETS))

        actual_by_id = {snapshot["assetId"]: snapshot for snapshot in snapshots}

        self.assertEqual(set(actual_by_id), set(expected_measurements))

        for asset_id, expected in expected_measurements.items():
            actual = actual_by_id[asset_id]

            self.assertEqual(actual["state"], expected.state)
            self.assertEqual(actual["temperature"], expected.temperature)
            self.assertEqual(actual["speed"], expected.speed)
            self.assertEqual(actual["alarm"], expected.alarm)


if __name__ == "__main__":
    unittest.main()
