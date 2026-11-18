"""Integration tests for the OPC UA client and server."""

import unittest

from asyncua import Client, Server
from asyncua.ua.uaerrors import UaStatusCodeError

from edge.industrial_gateway.opcua_client import IndustrialOPCUAClient
from simulator.industrial_assets.opcua_server import (
    NAMESPACE_URI,
    build_address_space,
)

TEST_ENDPOINT = "opc.tcp://127.0.0.1:4850/industrial/"

EXPECTED_ASSETS = {"M-101", "M-102", "P-101", "C-101", "F-101"}

EXPECTED_VARIABLES = {
    "state",
    "temperature",
    "speed",
    "alarm",
}


class TestOpcUaIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_client_reads_assets_and_server_rejects_writes(self):
        server = Server()
        await server.init()
        server.set_endpoint(TEST_ENDPOINT)
        await server.set_application_uri(NAMESPACE_URI)
        await build_address_space(server)

        async with server:
            async with IndustrialOPCUAClient(TEST_ENDPOINT) as client:
                snapshots = await client.read_assets()

                self.assertEqual(
                    {snapshot["assetId"] for snapshot in snapshots},
                    EXPECTED_ASSETS,
                )

                for snapshot in snapshots:
                    self.assertEqual(
                        set(snapshot) - {"assetId"},
                        EXPECTED_VARIABLES,
                    )
                    self.assertIsInstance(snapshot["state"], str)
                    self.assertIsInstance(snapshot["temperature"], float)
                    self.assertIsInstance(snapshot["speed"], float)
                    self.assertIsInstance(snapshot["alarm"], bool)

            # A separate network client verifies the server-side write restriction.
            async with Client(url=TEST_ENDPOINT) as write_client:
                namespace_index = await write_client.get_namespace_index(NAMESPACE_URI)

                temperature = await write_client.nodes.objects.get_child(
                    [
                        f"{namespace_index}:Factory",
                        f"{namespace_index}:M-101",
                        f"{namespace_index}:Temperature",
                    ]
                )

                with self.assertRaises(UaStatusCodeError):
                    await temperature.write_value(99.0)

                self.assertEqual(await temperature.read_value(), 0.0)


if __name__ == "__main__":
    unittest.main()
