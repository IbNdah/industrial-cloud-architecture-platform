"""OPC UA client for reading industrial asset telemetry."""

import logging
from typing import Any

from asyncua import Client

DEFAULT_ENDPOINT = "opc.tcp://127.0.0.1:4840/industrial/"
NAMESPACE_URI = "urn:industrial-cloud-architecture-platform"
VARIABLES = ("State", "Temperature", "Speed", "Alarm")

logger = logging.getLogger(__name__)


class IndustrialOPCUAClient:
    """Read telemetry variables exposed by the industrial OPC UA server."""

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT) -> None:
        self.endpoint = endpoint
        self._client: Client | None = None
        self._namespace_index: int | None = None

    async def connect(self) -> None:
        """Connect to the OPC UA server and resolve its namespace."""
        if self._client is not None:
            return

        client = Client(url=self.endpoint)
        await client.connect()
        try:
            namespace_index = await client.get_namespace_index(NAMESPACE_URI)
        except Exception:
            await client.disconnect()
            raise

        self._client = client
        self._namespace_index = namespace_index
        logger.info("Connected to OPC UA server at %s", self.endpoint)

    async def disconnect(self) -> None:
        """Disconnect from the OPC UA server if connected."""
        if self._client is not None:
            client = self._client
            self._client = None
            self._namespace_index = None
            await client.disconnect()
            logger.info("Disconnected from OPC UA server")

    async def read_assets(self) -> list[dict[str, Any]]:
        """Discover assets under Factory and read each asset's telemetry."""
        if self._client is None or self._namespace_index is None:
            raise RuntimeError("OPC UA client is not connected")

        factory = await self._client.nodes.objects.get_child(
            [f"{self._namespace_index}:Factory"]
        )
        asset_nodes = await factory.get_children()
        snapshots: list[dict[str, Any]] = []

        for asset_node in asset_nodes:
            asset_id = await asset_node.read_browse_name()
            snapshot: dict[str, Any] = {"assetId": asset_id.Name}

            for variable_name in VARIABLES:
                variable = await asset_node.get_child(
                    [f"{self._namespace_index}:{variable_name}"]
                )
                snapshot[variable_name[0].lower() + variable_name[1:]] = (
                    await variable.read_value()
                )

            snapshots.append(snapshot)

        return snapshots

    async def __aenter__(self) -> "IndustrialOPCUAClient":
        """Support use with ``async with``."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        """Always close the connection when leaving the context."""
        await self.disconnect()
