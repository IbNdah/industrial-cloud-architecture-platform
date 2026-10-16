# ADR-005: Edge Buffering and Message Delivery Semantics

**Status:** Accepted
**Date:** 2026-10-16
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.0.0

## 1. Context

Industrial telemetry must continue to be collected when connectivity between the Edge Gateway and Azure is interrupted.
The platform must preserve locally collected messages, recover after network or process failures, and avoid duplicate logical records when buffered messages are retransmitted.
The Edge Gateway must also handle limited local storage and make persistent delivery failures observable.

## 2. Decision

The Edge Gateway will use SQLite as a persistent local telemetry queue.
Messages will be stored before cloud transmission and retained until the configured MQTT delivery policy permits their removal.
The delivery model is **at least once**, with stable message identifiers and idempotent cloud processing to prevent duplicate logical effects.

The design combines:

- SQLite persistent storage.
- MQTT QoS 1 for telemetry publication.
- Retry with bounded backoff.
- Replay after connectivity restoration.
- Stable message identifiers.
- Cloud-side deduplication.
- Monitoring of queue size, message age and delivery failures.

## 3. Local Queue Design

Each queued message must include, at minimum:

- Stable message identifier.
- Asset identifier.
- Event timestamp.
- Serialized telemetry payload.
- Queue creation timestamp.
- Delivery status and retry metadata.

The queue must survive Edge Gateway process restarts.
SQLite transactions must be used to ensure that queue updates remain consistent when the process stops unexpectedly.
The implementation must define how concurrent queue operations are handled and how database integrity is checked after abnormal shutdowns.

## 4. Message Lifecycle

The expected lifecycle is:

1. Read measurements from the OPC UA Server.
2. Validate and normalize the telemetry.
3. Assign a stable message identifier.
4. Persist the message in SQLite.
5. Publish the message to Azure IoT Hub using MQTT QoS 1.
6. Process the MQTT acknowledgement and update the local delivery state.
7. After a successful MQTT PUBACK, mark the message as acknowledged and remove it from the pending queue according to the configured SQLite transaction and cleanup policy. If the process stops before the delivery state is durably updated, recover the message and retry publication when its delivery status is uncertain.
8. Deduplicate messages during cloud processing and persistence.

An MQTT PUBACK acknowledges the MQTT delivery step. It does not confirm that Azure Functions completed processing or that PostgreSQL committed the data.

For the initial implementation, the delivery guarantee is **at least once from the Edge Gateway to Azure IoT Hub**, not end-to-end delivery to PostgreSQL. Cloud-side idempotency must handle duplicates resulting from retries or recovery.

The implementation must test the recovery behavior for messages left in an intermediate state and document the queue deletion rule. An application-level acknowledgment confirming database persistence is outside the initial scope.

## 5. Retry and Replay Policy

When the cloud endpoint is unavailable or publication fails:

- Keep the message in SQLite.
- Retry after a configurable delay.
- Use bounded exponential backoff with jitter to avoid repeated synchronized retries.
- Resume transmission after connectivity is restored.
- Preserve the original message identifier and event timestamp.
- Record persistent failures for operational diagnosis.

Retry intervals and maximum retry rates must be configurable. Messages must not be silently discarded after an arbitrary retry count.

## 6. Buffer Capacity and Full-Queue Behavior

The queue must have an explicit storage limit based on available Edge storage and the expected telemetry rate.
The initial implementation must define and document:

- Maximum queue size.
- Expected telemetry volume and outage duration.
- Disk space reserved for operating system and application needs.
- Warning and critical queue thresholds.
- Behavior when the queue reaches capacity.

The queue must not silently overwrite undelivered telemetry.
If capacity is exhausted, the gateway must raise an observable critical condition and follow an explicit failure policy. The system must continue to protect local control functions. Whether new telemetry is rejected, sampling is reduced or another controlled response is used must be decided for the target deployment.

## 7. Deduplication and Idempotency

Each message identifier must remain unchanged across retries and replay.

Cloud processing must ensure that:

- Duplicate telemetry messages do not create duplicate logical records.
- Repeated processing does not create duplicate logical anomaly events.
- Database constraints or an equivalent atomic mechanism enforce deduplication.
- A failed transaction can be retried safely.

The deduplication key and retention period must be documented. Deduplication records must remain available for at least the maximum supported replay window.

## 8. Alternatives Considered

| Alternative | Decision |
|---|---|
| In-memory queue only | Rejected because queued telemetry would be lost after process restart |
| MQTT QoS 0 | Not selected as the default because it does not provide delivery acknowledgement |
| MQTT QoS 2 | Not available for device-to-cloud publishing through Azure IoT Hub |
| Unbounded local queue | Rejected because disk exhaustion could destabilize the Edge Gateway |
| Delete messages immediately after publication | Rejected because publication alone is not sufficient evidence of MQTT delivery acknowledgement |
| Exactly-once end-to-end processing | Not claimed; at-least-once delivery with idempotent processing is the selected design |

## 9. Consequences

### Positive

- Telemetry can survive temporary cloud outages and Edge process restarts.
- Retry and replay reduce the risk of telemetry loss caused by connectivity interruptions.
- Stable identifiers and deduplication prevent duplicate logical effects.
- Queue metrics improve operational visibility.

### Trade-offs

- Local storage capacity must be managed.
- Retries and replay can increase cloud traffic after an outage.
- MQTT acknowledgements do not guarantee downstream database persistence.
- SQLite integrity, transaction handling and recovery require testing.
- At-least-once delivery does not eliminate all data-loss risks, including hardware failure or storage corruption.

## 10. Verification Criteria

The decision is considered implemented when:

- Messages are persisted before transmission.
- Queued messages survive Edge Gateway process restarts.
- Messages remain available during a simulated cloud outage.
- Delivery resumes after connectivity restoration.
- MQTT QoS 1 acknowledgements are handled correctly.
- Retried messages retain their original identifiers.
- Duplicate messages do not create duplicate logical telemetry or anomaly records.
- Retry behavior is bounded and observable.
- Queue capacity thresholds and full-queue behavior are documented and tested.
- No undelivered message is silently removed by the normal queue policy.
- Local control remains operational when cloud connectivity is lost.

## 11. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [OT Architecture](../architecture/ot-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
- [ADR-001: Industrial Protocol and Edge-to-Cloud Communication](ADR-001-opcua-mqtt.md)
- [ADR-004: Industrial Network Segmentation and Security Boundaries](ADR-004-industrial-network-segmentation.md)
