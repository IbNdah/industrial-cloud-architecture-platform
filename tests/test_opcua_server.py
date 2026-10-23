"""Tests for the industrial OPC UA server."""

import unittest

from asyncua import Server, ua

from edge.industrial_gateway.opcua_server import build_address_space


class TestOpcUaAddressSpace(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = Server()
        await self.server.init()
        self.asset_nodes = await build_address_space(self.server)

    async def test_all_industrial_assets_are_exposed(self):
        self.assertEqual(
            set(self.asset_nodes),
            {"M-101", "M-102", "P-101", "C-101", "F-101"},
        )

    async def test_each_asset_has_expected_variables(self):
        expected_variables = {
            "state",
            "temperature",
            "speed",
            "alarm",
        }

        for nodes in self.asset_nodes.values():
            self.assertEqual(set(nodes), expected_variables)

    async def test_variables_are_read_only_for_clients(self):
        for nodes in self.asset_nodes.values():
            for node in nodes.values():
                access_level = await node.read_attribute(
                    ua.AttributeIds.UserAccessLevel
                )
                writable = (
                    int(access_level.Value.Value) & ua.AccessLevel.CurrentWrite.mask
                )

                self.assertEqual(writable, 0)

    async def test_initial_values_have_expected_types(self):
        for nodes in self.asset_nodes.values():
            self.assertIsInstance(await nodes["state"].read_value(), str)
            self.assertIsInstance(await nodes["temperature"].read_value(), float)
            self.assertIsInstance(await nodes["speed"].read_value(), float)
            self.assertIsInstance(await nodes["alarm"].read_value(), bool)


if __name__ == "__main__":
    unittest.main()
