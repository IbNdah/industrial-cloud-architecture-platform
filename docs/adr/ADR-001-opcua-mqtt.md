# ADR-001: Industrial Protocol and Edge-to-Cloud Communication

**Status:** Accepted
**Date:** 2026-10-16
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.2.0

## 1. Context

The Industrial Asset Monitoring Platform must acquire telemetry from industrial equipment and securely transmit it to Azure for processing and visualization.

The architecture must preserve local control, isolate industrial systems from cloud services, tolerate temporary connectivity outages and support future multi-factory deployments.

Two communication boundaries must be addressed:

1. Industrial equipment and the Edge Gateway.
2. The Edge Gateway and the Azure cloud platform.

The communication design must remain simple for the initial monitoring use case while allowing future extensions if operational requirements justify them.

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

### 2.3 Communication Direction and Scope

The initial implementation uses a unidirectional telemetry flow:

#### Edge Gateway -> Azure IoT Hub

The Edge Gateway publishes industrial telemetry to IoT Hub. The cloud platform receives and processes these messages through the configured ingestion pipeline.

Although Azure IoT Hub supports additional device-management and cloud-to-device capabilities, these are not required for the initial monitoring scope.

The following capabilities are deferred:

- Cloud-to-device messages for notifications or configuration delivery.
- Direct Methods for request-response operations on a specific device.
- Device Twins for desired and reported configuration synchronization.

These capabilities may be evaluated in a future architecture iteration if a concrete operational requirement emerges.

The initial architecture does not implement remote control of PLCs. Any future cloud-originated operation must preserve local industrial safety mechanisms and must not bypass PLC interlocks or local control logic.

### 2.4 MQTT Broker and Messaging Architecture

Azure IoT Hub is used as a managed device connectivity and telemetry ingestion service. It is not treated as a general-purpose MQTT broker.

A separate MQTT broker is not introduced because the initial use case requires authenticated device telemetry ingestion rather than general-purpose publish-subscribe communication between multiple applications or devices.

Azure Event Grid MQTT capabilities or a dedicated MQTT broker may be evaluated later if requirements include:

- Flexible MQTT topic hierarchies and subscriptions.
- Many-to-many communication between devices and applications.
- Message fan-out to multiple independent consumers.
- Device-to-device communication or broader MQTT messaging patterns.

These capabilities are outside the initial architecture scope.

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

| Alternative | Decision |
| --- | --- |
| Direct PLC-to-cloud communication | Rejected because it increases OT exposure and couples control infrastructure to cloud connectivity |
| Proprietary industrial protocol | Not selected because it may reduce interoperability across equipment vendors |
| HTTP/REST for continuous Edge telemetry | Not selected because MQTT provides lightweight telemetry messaging and acknowledgement-based delivery |
| Separate cloud MQTT broker | Deferred because IoT Hub provides the required device ingestion capabilities |
| General-purpose MQTT broker or Event Grid MQTT | Deferred until flexible topic routing, fan-out or many-to-many messaging is required |
| MQTT QoS 0 as the default | Not selected because it does not provide MQTT delivery acknowledgement |
| MQTT QoS 2 | Not selected because it is not supported for device-to-cloud publishing by Azure IoT Hub |
| Cloud-dependent local control | Rejected because industrial control must continue during cloud outages |
| Cloud-to-device communication in the initial implementation | Deferred because the current scope is telemetry monitoring, not remote device management or control |

## 6. Consequences

### Positive

- Clear separation between industrial data acquisition and cloud ingestion.
- Reduced direct exposure of OT systems.
- Persistent buffering and replay during network interruptions.
- MQTT acknowledgement and stable message identity support reliable delivery.
- Idempotent processing reduces duplicate effects.
- Reusable communication patterns across multiple industrial assets.
- Limited initial scope reduces implementation and operational complexity.

### Trade-offs

- OPC UA configuration and certificate management require implementation effort.
- Edge buffering requires capacity limits, retry policies and operational monitoring.
- QoS 1 can produce duplicate deliveries.
- End-to-end reliability depends on correct buffer handling, routing, processing and persistence.
- Future bidirectional communication will require additional device-side and cloud-side components.
- A separate MQTT messaging service may become necessary if future requirements exceed IoT Hub's device-ingestion capabilities.

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
- Buffer-full conditions and persistent delivery failures are observable.
- No direct cloud-to-PLC control path exists.
- The local control path remains independent of cloud availability.
- The initial implementation does not depend on cloud-to-device messaging.

## 8. Conditions for Reassessment

Reassess this decision if operational requirements introduce:

- Remote device configuration or diagnostics.
- Cloud-to-device notifications or commands.
- Device Twin synchronization.
- Multiple independent MQTT publishers and subscribers requiring flexible topic routing.
- Message fan-out or device-to-device communication.
- Requirements that justify a dedicated MQTT messaging service.

Any future extension involving industrial commands must undergo a separate security and safety assessment.

## 9. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [OT Architecture](../architecture/ot-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
- [ADR-002: Cloud Ingestion and Event Processing](ADR-002-cloud-ingestion-processing.md)
