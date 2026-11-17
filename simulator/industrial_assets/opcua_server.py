"""OPC UA server for simulated industrial assets."""

import asyncio
import logging

from asyncua import Server
from asyncua.common.node import Node

from simulator.industrial_assets.models import AssetConfig
from simulator.industrial_assets.simulator import ASSETS, IndustrialSimulator

ENDPOINT = "opc.tcp://127.0.0.1:4840/industrial/"
NAMESPACE_URI = "urn:industrial-cloud-architecture-platform"
UPDATE_INTERVAL_SECONDS = 5
ASSETS_BY_ID = {asset.asset_id: asset for asset in ASSETS}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Reduce verbose internal address-space messages from asyncua.
logging.getLogger("asyncua.server.address_space").setLevel(logging.WARNING)


async def build_address_space(
    server: Server,
) -> dict[str, dict[str, Node | AssetConfig]]:
    """Create the factory, assets, and read-only telemetry variables."""
    namespace_index = await server.register_namespace(NAMESPACE_URI)
    factory = await server.nodes.objects.add_object(namespace_index, "Factory")

    asset_nodes: dict[str, dict[str, Node]] = {}

    for asset in ASSETS:
        asset_node = await factory.add_object(namespace_index, asset.asset_id)

        variables = {
            "state": await asset_node.add_variable(namespace_index, "State", "STOPPED"),
            "temperature": await asset_node.add_variable(
                namespace_index, "Temperature", 0.0
            ),
            "speed": await asset_node.add_variable(namespace_index, "Speed", 0.0),
            "alarm": await asset_node.add_variable(namespace_index, "Alarm", False),
        }

        for variable in variables.values():
            await variable.set_writable(False)

        asset_nodes[asset.asset_id] = variables

    return asset_nodes


async def update_telemetry(
    asset_nodes: dict[str, dict[str, Node | AssetConfig]],
    simulator: IndustrialSimulator,
) -> None:
    """Generate and publish one telemetry snapshot per asset."""
    for asset_id, nodes in asset_nodes.items():
        config = ASSETS_BY_ID[asset_id]
        measurement = simulator.generate_telemetry(config)

        await nodes["state"].write_value(measurement.state)
        await nodes["temperature"].write_value(measurement.temperature)
        await nodes["speed"].write_value(measurement.speed)
        await nodes["alarm"].write_value(measurement.alarm)

        logger.info(
            "%s | state=%s temperature=%.2f speed=%.2f alarm=%s",
            asset_id,
            measurement.state,
            measurement.temperature,
            measurement.speed,
            measurement.alarm,
        )


async def main() -> None:
    """Initialize and run the OPC UA server."""
    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    await server.set_application_uri(NAMESPACE_URI)

    asset_nodes = await build_address_space(server)
    simulator = IndustrialSimulator()

    logger.info("Starting OPC UA server at %s", ENDPOINT)

    try:
        async with server:
            while True:
                await update_telemetry(asset_nodes, simulator)
                await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
    finally:
        logger.info("OPC UA server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
