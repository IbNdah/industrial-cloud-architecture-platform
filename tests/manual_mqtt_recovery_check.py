"""Manual recovery check for pending MQTT telemetry."""

import asyncio

from edge.industrial_gateway.mqtt_publisher import MqttPublisher
from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer


async def main():
    database_path = "data/mqtt_resilience_test.db"

    buffer = SQLiteTelemetryBuffer(database_path=database_path)
    await buffer.initialize()

    publisher = MqttPublisher(
        buffer=buffer,
        host="127.0.0.1",
        port=1883,
    )

    try:
        pending_before = await buffer.get_pending()
        print(f"Pending messages before recovery: {len(pending_before)}")

        publisher.connect()
        published_count = await publisher.publish_pending()

        pending_after = await buffer.get_pending()
        print(f"Published messages: {published_count}")
        print(f"Remaining pending messages: {len(pending_after)}")

    finally:
        publisher.disconnect()
        await buffer.close()


if __name__ == "__main__":
    asyncio.run(main())
