"""Orchestrate the industrial edge gateway components."""

import asyncio
import logging
from datetime import UTC, datetime

from edge.industrial_gateway.mqtt_publisher import MqttPublisher
from edge.industrial_gateway.opcua_client import IndustrialOPCUAClient
from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer
from edge.industrial_gateway.telemetry_validator import normalize_telemetry

logger = logging.getLogger(__name__)

ACQUISITION_INTERVAL_SECONDS = 5


class IndustrialGateway:
    """Coordinate OPC UA acquisition, SQLite buffering and MQTT delivery."""

    def __init__(
        self,
        opcua_endpoint: str = "opc.tcp://127.0.0.1:4840/industrial/",
        mqtt_host: str = "127.0.0.1",
        mqtt_port: int = 1883,
        database_path: str = "data/edge_buffer.db",
    ) -> None:
        # Instantiate the components without opening connections.
        self.opcua_client = IndustrialOPCUAClient(endpoint=opcua_endpoint)
        self.buffer = SQLiteTelemetryBuffer(database_path=database_path)
        self.publisher = MqttPublisher(
            buffer=self.buffer,
            host=mqtt_host,
            port=mqtt_port,
        )

        self._started = False

    async def start(self) -> None:
        """Initialize storage and connect gateway components."""
        if self._started:
            return

        await self.buffer.initialize()

        try:
            # Start MQTT independently of OPC UA connection establishment.
            self.publisher.connect()
            await self.opcua_client.connect()
        except Exception:
            self.publisher.disconnect()
            await self.buffer.close()
            raise

        self._started = True
        logger.info("Industrial Gateway started")

    async def run(self) -> None:
        """Acquire, validate, buffer and publish telemetry periodically."""
        if not self._started:
            raise RuntimeError("Industrial Gateway is not started")

        logger.info(
            "Starting telemetry acquisition every %s seconds",
            ACQUISITION_INTERVAL_SECONDS,
        )

        while True:
            try:
                # Isolate OPC UA failures so MQTT delivery can continue.
                raw_snapshots = await self.opcua_client.read_assets()

            except Exception:
                logger.exception("OPC UA acquisition failed")

                try:
                    # Replace the failed session before the next acquisition cycle.
                    await self.opcua_client.reconnect()
                except Exception:
                    logger.exception("OPC UA reconnection failed")

            else:
                for raw_snapshot in raw_snapshots:
                    try:
                        # Timestamp telemetry at the Edge acquisition point.
                        snapshot = normalize_telemetry(
                            raw=raw_snapshot,
                            observed_at=datetime.now(UTC),
                        )
                    except (ValueError, KeyError) as exc:
                        # Reject invalid assets without blocking valid ones.
                        logger.warning(
                            "Telemetry rejected for %s: %s",
                            raw_snapshot.get("assetId", "unknown"),
                            exc,
                        )
                        continue

                    # Persist before attempting delivery to preserve at-least-once behavior.
                    await self.buffer.add(snapshot)

            try:
                # MQTT delivery remains independent of OPC UA availability.
                if self.publisher.is_connected:
                    published_count = await self.publisher.publish_pending()

                    if published_count:
                        logger.info(
                            "Published %s pending telemetry messages",
                            published_count,
                        )
            except Exception:
                logger.exception("MQTT delivery cycle failed")

            await asyncio.sleep(ACQUISITION_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """Disconnect components and release resources."""
        if not self._started:
            return

        try:
            await self.opcua_client.disconnect()
        finally:
            try:
                self.publisher.disconnect()
            finally:
                await self.buffer.close()
                self._started = False

        logger.info("Industrial Gateway stopped")


async def main() -> None:
    """Start the gateway and ensure resources are released on shutdown."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    gateway = IndustrialGateway()
    await gateway.start()

    try:
        await gateway.run()
    finally:
        # Ensure connections and persistent storage are closed on cancellation.
        await gateway.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Gateway stopped by user")
