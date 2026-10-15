# ADR-001: Industrial Protocol and Edge-to-Cloud Communication

**Status:** Accepted
**Date:** 2026-10-15
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.0.0

## 1. Context

The Industrial Asset Monitoring Platform must acquire telemetry from industrial equipment and securely transmit it to Azure for processing and visualization.

The architecture must preserve local control, isolate industrial systems from cloud services, tolerate temporary connectivity outages, and support future multi-factory deployments.

Two communication boundaries must be addressed:

1. Industrial equipment and the Edge Gateway.
2. The Edge Gateway and the Azure cloud platform.

## 2. Decision

### 2.1 Industrial Communication: OPC UA

OPC UA is selected as the industrial data access protocol between the OPC UA Server and the Edge Gateway.

The Edge Gateway acts as an OPC UA client and reads authorized measurements exposed by the server.

Responsibilities include:

- Reading configured asset measurements.
- Validating and normalizing telemetry.
- Handling communication errors and reconnection.
- Avoiding any dependency on cloud connectivity for local control.

The initial implementation is read-only. Remote PLC commands are outside the project scope.

### 2.2 Edge-to-Cloud Communication: MQTT over TLS

MQTT over TLS is selected for telemetry transmission from the Edge Gateway to Azure IoT Hub.

The Edge Gateway must:

- Authenticate using a provisioned device identity.
- Validate the cloud endpoint and TLS certificate.
- Publish telemetry using a defined message schema.
- Persist messages locally when cloud connectivity is unavailable.
- Replay buffered messages after reconnection.
- Include a stable message identifier to support duplicate detection.

Azure IoT Hub is the selected cloud ingestion endpoint. A separate MQTT broker is not required in the initial cloud architecture.

## 3. Network and Security Principles

- OT, Industrial DMZ and Cloud must be separated by defined security boundaries.
- Communication from the Edge Gateway to Azure is outbound and restricted to approved destinations and ports.
- The cloud must not establish a direct control path to PLCs.
- OPC UA access must be restricted to authorized clients and endpoints.
- TLS certificates and device credentials must be managed and revocable.
- Firewall rules must be validated against the actual deployment environment.

The exact ports and network routes will be documented during implementation.

## 4. Reliability

The Edge Gateway uses persistent SQLite storage to buffer telemetry during connectivity outages.

The delivery model is **at least once**: a message may be delivered more than once after a retry or replay. A stable message identifier and cloud-side deduplication must prevent duplicate processing from creating duplicate logical records or anomaly events.

Local control and supervision remain operational during cloud outages. Cloud monitoring and dashboards may become temporarily stale until connectivity is restored and queued telemetry is processed.

## 5. Alternatives Considered

| Alternative | Reason Not Selected |
|---|---|
| Direct PLC-to-cloud communication | Increases OT exposure and couples control infrastructure to cloud connectivity |
| Proprietary or vendor-specific industrial protocol | Reduces interoperability across equipment vendors |
| HTTP/REST for continuous Edge telemetry | Possible, but MQTT is a better fit for lightweight telemetry messaging and reconnect scenarios |
| Separate cloud MQTT broker | Adds operational complexity without a demonstrated requirement because IoT Hub provides the cloud ingestion endpoint |
| Cloud-dependent local control | Rejected because industrial control must continue during cloud outages |

## 6. Consequences

### Positive

- Clear separation between industrial data acquisition and cloud ingestion.
- Reduced direct exposure of OT systems.
- Interoperable industrial data access.
- Persistent buffering and replay during network interruptions.
- Reusable communication patterns across multiple industrial assets.

### Trade-offs

- OPC UA server configuration and certificate management require implementation effort.
- Edge buffering requires storage limits, retry policies and operational monitoring.
- At-least-once delivery requires idempotent processing and deduplication.
- Firewall, DNS and certificate requirements depend on the target environment.

## 7. Verification Criteria

The decision is considered implemented when:

- The Edge Gateway reads configured telemetry from an OPC UA Server.
- Invalid telemetry is rejected or logged according to the validation policy.
- The Edge Gateway publishes telemetry to IoT Hub over authenticated TLS.
- Device identity can be revoked.
- Telemetry remains queued during a simulated cloud outage.
- Queued telemetry is replayed after connectivity returns.
- Duplicate messages do not create duplicate logical records or anomaly events.
- No direct cloud-to-PLC control path exists.
- The local control path remains independent of cloud availability.

## 8. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [OT Architecture](../architecture/ot-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
