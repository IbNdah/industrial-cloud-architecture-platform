# ADR-001: Industrial Protocol and Edge-to-Cloud Communication

**Status:** Accepted
**Date:** 2026-10-16
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.1.0

## 1. Context

The Industrial Asset Monitoring Platform must acquire telemetry from industrial equipment and securely transmit it to Azure for processing and visualization.
The architecture must preserve local control, isolate industrial systems from cloud services, tolerate temporary connectivity outages and support future multi-factory deployments.

Two communication boundaries must be addressed:

1. Industrial equipment and the Edge Gateway.
2. The Edge Gateway and the Azure cloud platform.

## 2. Decision

### 2.1 Industrial Communication: OPC UA

OPC UA is selected for industrial data access between the OPC UA Server and the Edge Gateway.
The Edge Gateway acts as an OPC UA client and reads authorized measurements exposed by the server.

Responsibilities include:

- Reading configured asset measurements.
- Validating and normalizing telemetry.
- Handling communication errors and reconnection.
- Operating independently of cloud availability for local control.

The initial implementation is read-only. Remote PLC commands are outside the project scope.

### 2.2 Edge-to-Cloud Communication: MQTT over TLS

MQTT over TLS is selected for telemetry transmission from the Edge Gateway to Azure IoT Hub.
The Edge Gateway must:

- Authenticate using a provisioned device identity.
- Validate the cloud endpoint and TLS certificate.
- Publish telemetry using a defined message schema.
- Use MQTT QoS 1 for telemetry publication.
- Persist messages locally in SQLite until the configured delivery policy permits their removal.
- Retry publication and replay buffered messages after reconnection.
- Include a stable message identifier to support cloud-side deduplication.

Azure IoT Hub is the selected cloud ingestion endpoint. A separate MQTT broker is not required in the initial cloud architecture.

## 3. Delivery Semantics and Reliability

### 3.1 MQTT QoS 1

QoS 1 provides at-least-once MQTT delivery. The publisher expects a PUBACK acknowledgement from the MQTT endpoint. If acknowledgement is not received, the message may be retransmitted.
Duplicate delivery is therefore possible.
PUBACK confirms the MQTT delivery step; it does not prove that Azure Functions processed the message or that PostgreSQL committed the corresponding record.

### 3.2 Persistent Edge Buffer

SQLite provides persistent local buffering during cloud connectivity outages.
The Edge Gateway must preserve messages across process restarts and retry delivery after connectivity is restored.

The implementation must define:

- When a buffered message can be marked as delivered and removed.
- How unacknowledged messages are retried.
- Maximum buffer size and behavior when the buffer is full.
- Retry intervals and backoff.
- Monitoring for queue growth and delivery failures.

The buffer must not silently discard telemetry. Any configured retention limit or data-loss policy must be explicit and observable.

### 3.3 Stable Message Identity and Deduplication

Each telemetry message must include a stable, unique message identifier that remains unchanged during retries and replay.
Cloud processing and persistence must be idempotent. Reprocessing the same message must not create duplicate logical telemetry records or anomaly events.
The identifier and deduplication policy must be implemented consistently across the Edge Gateway, Azure Functions and PostgreSQL persistence layer.

### 3.4 End-to-End Guarantee

The target delivery model is at least once, with idempotent processing to prevent duplicate logical effects.
The architecture does not claim exactly-once delivery or processing across the complete Edge-to-PostgreSQL pipeline.

## 4. Network and Security Principles

- OT, Industrial DMZ and Cloud must be separated by defined security boundaries.
- Communication from the Edge Gateway to Azure must be outbound and restricted to approved destinations and ports.
- The cloud must not establish a direct control path to PLCs.
- OPC UA access must be restricted to authorized clients and endpoints.
- TLS and device credentials must be managed and revocable.
- Firewall rules must be validated against the target deployment environment.
- Credentials and certificates must not be embedded in source code or committed configuration files.

Exact ports, routes and certificate provisioning procedures will be documented during implementation.

## 5. Alternatives Considered

| Alternative | Reason Not Selected |
|---|---|
| Direct PLC-to-cloud communication | Increases OT exposure and couples control infrastructure to cloud connectivity |
| Proprietary industrial protocol | May reduce interoperability across equipment vendors |
| HTTP/REST for continuous Edge telemetry | MQTT is selected for lightweight telemetry messaging and acknowledgement-based delivery |
| Separate cloud MQTT broker | Adds complexity because IoT Hub provides the cloud ingestion endpoint |
| MQTT QoS 0 as the default | Does not provide MQTT delivery acknowledgement |
| MQTT QoS 2 | Not supported for device-to-cloud publishing by Azure IoT Hub |
| Cloud-dependent local control | Rejected because industrial control must continue during cloud outages |

## 6. Consequences

### Positive

- Clear separation between industrial data acquisition and cloud ingestion.
- Reduced direct exposure of OT systems.
- Persistent buffering and replay during network interruptions.
- MQTT acknowledgement and stable message identity support reliable delivery.
- Idempotent processing reduces duplicate effects.
- Reusable communication patterns across multiple industrial assets.

### Trade-offs

- OPC UA configuration and certificate management require implementation effort.
- Edge buffering requires capacity limits, retry policies and operational monitoring.
- QoS 1 can produce duplicate deliveries.
- End-to-end reliability depends on correct buffer handling, routing, processing and persistence.
- The design requires explicit failure handling and deduplication tests.

## 7. Verification Criteria

The decision is considered implemented when:

- The Edge Gateway reads configured telemetry from an OPC UA Server.
- Invalid telemetry is rejected or logged according to the validation policy.
- The Edge Gateway publishes telemetry to IoT Hub over authenticated TLS using QoS 1.
- MQTT delivery acknowledgements are handled correctly.
- Device identity can be revoked.
- Telemetry remains queued during a simulated cloud outage and survives an Edge process restart.
- Queued telemetry is replayed after connectivity returns.
- Retransmission does not create duplicate logical records or anomaly events.
- Buffer-full conditions and persistent delivery failures are observable
- No direct cloud-to-PLC control path exists.
- The local control path remains independent of cloud availability.

## 8. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [OT Architecture](../architecture/ot-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
