"""Manual MQTT resilience check with a persistent test database."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from edge.industrial_gateway.mqtt_publisher import MqttPublisher
from edge.industrial_gateway.sqlite_buffer import SQLiteTelemetryBuffer
from edge.industrial_gateway.telemetry import TelemetrySnapshot


async def main():
    database_path = Path("data/mqtt_resilience_test.db")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    buffer = SQLiteTelemetryBuffer(database_path=str(database_path))
    await buffer.initialize()

    snapshot = TelemetrySnapshot(
        schema_version="1.0",
        asset_id="M-101",
        asset_type="electric_motor",
        observed_at=datetime.now(UTC),
        state="RUNNING",
        temperature=65.5,
        speed=1450.0,
        alarm=False,
    )

    message_id = await buffer.add(snapshot)
    print(f"SQLite message created: ID={message_id}")

    publisher = MqttPublisher(
        buffer=buffer,
        host="127.0.0.1",
        port=1883,
    )

    try:
        publisher.connect()
        published_count = await publisher.publish_pending()
        print(f"Published messages: {published_count}")

    except Exception as exc:
        print(f"Publication failed: {type(exc).__name__}: {exc}")

    finally:
        pending_messages = await buffer.get_pending()
        print(f"Remaining pending messages: {len(pending_messages)}")

        for message in pending_messages:
            print(f"Pending message ID: {message['id']}")

        publisher.disconnect()
        await buffer.close()


if __name__ == "__main__":
    asyncio.run(main())
