# Architecture Requirements

**Status:** Draft — S1.4
**Version:** 0.1.0

## 1. Purpose

Define the functional and non-functional requirements for the Industrial Asset Monitoring Platform.

Each requirement has a unique ID, a priority, and a verification criterion.

## 2. Requirements

| ID | Requirement | Priority | Verification criterion |
|---|---|---|---|
| AR-01 | Local industrial control must continue during cloud outages. | P0 | Simulated cloud disconnection does not affect local control. |
| AR-02 | The cloud must not have a direct control path to PLCs. | P0 | Architecture and network rules contain no cloud-to-PLC control flow. |
| AR-03 | The Edge Gateway must acquire telemetry from an OPC UA server. | P0 | Valid OPC UA measurements are received by the gateway. |
| AR-04 | Edge-to-cloud communication must use TLS. | P0 | The configured cloud connection uses authenticated TLS. |
| AR-05 | Each Edge Gateway must have an identifiable and revocable identity. | P0 | A gateway can be identified and its access revoked. |
| AR-06 | The Edge Gateway must persist telemetry locally during cloud connectivity outages. | P0 | Messages remain queued after a simulated outage and gateway restart. |
| AR-07 | Queued telemetry must be replayed after connectivity is restored. | P0 | Buffered messages are delivered after reconnection. |
| AR-08 | Telemetry must be validated before processing. | P0 | Invalid schema, missing asset ID, or invalid timestamps are rejected or quarantined. |
| AR-09 | Configured threshold violations must generate alarms. | P0 | Test telemetry exceeding a configured threshold produces an alarm. |
| AR-10 | Edge and cloud processing failures must be observable. | P1 | Logs or metrics expose connectivity, queue, and processing errors. |
| AR-11 | Infrastructure must be deployable through Terraform. | P1 | Terraform validation succeeds and the documented deployment procedure is reproducible. |
| AR-12 | The asset model must support multiple factories without a fundamental redesign. | P2 | The data model can represent assets belonging to at least two factories. |

## 3. Priority Definitions

| Priority | Meaning |
|---|---|
| P0 | Required for the initial demonstrator |
| P1 | Required for a reliable and maintainable implementation |
| P2 | Future extensibility requirement |

## 4. Verification Approach

| Area | Verification method |
|---|---|
| OT continuity | Simulate cloud connectivity loss and verify local operation remains independent |
| Edge buffering | Disconnect cloud connectivity, restart the gateway, and inspect the persisted queue |
| Replay and deduplication | Restore connectivity and verify delivery without duplicate business records |
| Security | Review TLS configuration, identity provisioning, and permitted network flows |
| Telemetry validation | Submit valid and invalid messages |
| Alarm generation | Submit measurements above and below configured thresholds |
| Observability | Trigger controlled errors and inspect logs and metrics |
| Infrastructure | Run Terraform formatting, validation, and deployment checks |
| Multi-factory model | Create assets associated with two distinct factories |

## 5. Assumptions and Constraints

- The initial implementation uses simulated industrial equipment and a simulated OPC UA server.
- Local control is represented architecturally; the demonstrator does not control real PLCs.
- Anomaly detection initially uses configurable rules, not machine learning.
- Telemetry delivery may be at-least-once. Cloud processing must handle duplicate message IDs.
- Azure service configuration and Terraform support must be validated during implementation.

## 6. Related Documents

- `context.md` — project purpose and scope.
- `ot-architecture.md` — industrial components and behavior.
- `gap-analysis.md` — reuse and implementation gaps.
- `high-level-architecture.md` — end-to-end architecture.
- `security-architecture.md` — security controls.
- `technology-mapping.md` — Azure service mapping.
- `../adr/` — Architecture Decision Records.
