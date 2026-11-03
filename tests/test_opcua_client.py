"""Unit tests for the industrial OPC UA client."""

import unittest
from unittest.mock import AsyncMock, MagicMock

from edge.industrial_gateway.opcua_client import IndustrialOPCUAClient


class TestIndustrialOPCUAClient(unittest.IsolatedAsyncioTestCase):
    """Test client behavior without requiring a running OPC UA server."""

    async def test_read_assets_requires_connection(self):
        """Reading telemetry before connecting must fail clearly."""
        client = IndustrialOPCUAClient()

        with self.assertRaisesRegex(RuntimeError, "not connected"):
            await client.read_assets()

    async def test_read_assets_returns_all_assets_and_variables(self):
        """Read four telemetry variables for each of the five assets."""
        client = IndustrialOPCUAClient()
        client._client = MagicMock()
        client._namespace_index = 2

        factory = MagicMock()
        client._client.nodes.objects.get_child = AsyncMock(return_value=factory)

        asset_ids = ["M-101", "M-102", "P-101", "C-101", "F-101"]
        asset_nodes = []

        for asset_id in asset_ids:
            asset_node = MagicMock()
            browse_name = MagicMock()
            browse_name.Name = asset_id
            asset_node.read_browse_name = AsyncMock(return_value=browse_name)

            async def get_child(path, *, _asset_id=asset_id):
                variable_name = path[0].split(":", 1)[1]
                variable = MagicMock()
                values = {
                    "State": "RUNNING",
                    "Temperature": 42.5,
                    "Speed": 1200.0,
                    "Alarm": False,
                }
                variable.read_value = AsyncMock(return_value=values[variable_name])
                return variable

            asset_node.get_child = AsyncMock(side_effect=get_child)
            asset_nodes.append(asset_node)

        factory.get_children = AsyncMock(return_value=asset_nodes)

        snapshots = await client.read_assets()

        self.assertEqual(len(snapshots), 5)
        self.assertEqual([item["assetId"] for item in snapshots], asset_ids)

        expected_values = {
            "state": "RUNNING",
            "temperature": 42.5,
            "speed": 1200.0,
            "alarm": False,
        }
        for snapshot in snapshots:
            for key, expected in expected_values.items():
                self.assertEqual(snapshot[key], expected)

        client._client.nodes.objects.get_child.assert_awaited_once_with(["2:Factory"])
        for asset_node in asset_nodes:
            self.assertEqual(asset_node.get_child.await_count, 4)

    async def test_disconnect_clears_client_state(self):
        """Disconnect should close the session and reset internal state."""
        client = IndustrialOPCUAClient()
        mock_connection = MagicMock()
        mock_connection.disconnect = AsyncMock()
        client._client = mock_connection
        client._namespace_index = 2

        await client.disconnect()

        mock_connection.disconnect.assert_awaited_once()
        self.assertIsNone(client._client)
        self.assertIsNone(client._namespace_index)

    async def test_disconnect_when_not_connected_is_safe(self):
        """Disconnecting an unused client should not raise."""
        client = IndustrialOPCUAClient()

        await client.disconnect()

        self.assertIsNone(client._client)
        self.assertIsNone(client._namespace_index)


if __name__ == "__main__":
    unittest.main()
