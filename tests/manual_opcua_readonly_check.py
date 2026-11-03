"""Manual integration check for the OPC UA server."""

import asyncio

from asyncua import Client, ua

ENDPOINT = "opc.tcp://127.0.0.1:4840/industrial/"
NAMESPACE_URI = "urn:industrial-cloud-architecture-platform"


async def main():
    async with Client(url=ENDPOINT) as client:
        namespace_index = await client.get_namespace_index(NAMESPACE_URI)

        temperature = client.get_node(
            ua.NodeId(
                "Temperature",
                namespace_index,
            )
        )

        # Browse to the actual variable below M-101.
        objects = client.nodes.objects
        factory = await objects.get_child([f"{namespace_index}:Factory"])
        motor = await factory.get_child([f"{namespace_index}:M-101"])
        temperature = await motor.get_child([f"{namespace_index}:Temperature"])

        value = await temperature.read_value()
        print(f"M-101 temperature: {value} °C")

        try:
            await temperature.write_value(999.0)
        except Exception as exc:
            print(f"Write rejected: {type(exc).__name__}")
        else:
            raise AssertionError(
                "Unexpectedly, the client was able to write Temperature."
            )


if __name__ == "__main__":
    asyncio.run(main())
