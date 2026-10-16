# ADR-002: Cloud Ingestion and Event Processing

**Status:** Accepted
**Date:** 2026-10-16
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.0.0

## 1. Context

The platform must ingest industrial telemetry from the Edge Gateway, process incoming messages, detect anomalies and persist the results for dashboards and operational analysis.
The solution should reuse Azure managed services, remain straightforward to operate and avoid introducing infrastructure that is not justified by the initial workload.

## 2. Decision

The initial cloud processing architecture uses:

- **Azure IoT Hub** for authenticated device connectivity and telemetry ingestion.
- **Azure Functions** for event-driven telemetry processing and rule-based anomaly detection.
- **Azure Database for PostgreSQL Flexible Server** for telemetry, asset state and anomaly persistence.
- **DashboardService API** for application-facing queries.
- **Grafana** for visualization.

Telemetry will be routed from IoT Hub to the Azure Functions processing component using the IoT Hub built-in Event Hubs-compatible endpoint and an Azure Functions Event Hub trigger.

## 3. Processing Responsibilities

The processing function must:

1. Validate the message schema and required fields.
2. Check asset identity and telemetry timestamps.
3. Handle duplicate messages using a stable message identifier.
4. Evaluate configured thresholds and anomaly rules.
5. Persist telemetry and anomaly events consistently.
6. Record processing errors and expose operational signals.

Processing must be designed for retries. A repeated delivery must not create duplicate logical records or duplicate anomaly events.

## 4. Alternatives Considered

| Alternative | Decision |
|---|---|
| Separate Azure Event Hubs namespace | Deferred until independent consumers, throughput or retention requirements justify it |
| Azure Kubernetes Service (AKS) | Not selected for the initial workload; adds cluster operations and platform overhead |
| Self-managed message broker in Azure | Not selected because IoT Hub already provides device ingestion |
| Direct database writes from Edge | Rejected because it bypasses the controlled cloud ingestion and processing path |
| Machine-learning-based anomaly detection | Deferred until representative data and measurable evaluation criteria are available |

## 5. Consequences

### Positive

- Managed cloud ingestion and event-driven processing.
- Clear separation between device connectivity, processing, persistence and visualization.
- Lower operational complexity than a Kubernetes-based solution.
- Reuse of patterns from the existing EV Fleet Monitoring Platform.

### Trade-offs

- Function retries and duplicate delivery must be handled explicitly.
- Database connectivity, transaction boundaries and retry behavior require careful design.
- Throughput, concurrency and database connection limits must be validated under load.
- A separate streaming service may be required if future workloads introduce additional consumers or stronger streaming requirements.

## 6. Security and Reliability

- Edge devices authenticate using provisioned IoT Hub identities.
- Cloud services use managed identities where supported.
- PostgreSQL must not be exposed publicly without a justified and approved exception.
- Secrets must not be stored in source code or committed configuration files.
- Processing failures must be observable through Azure Monitor and Application Insights.
- Local Edge buffering remains responsible for tolerating temporary cloud connectivity loss.

## 7. Verification Criteria

The decision is considered implemented when:

- IoT Hub receives telemetry from an authenticated Edge identity.
- The configured route delivers telemetry to Azure Functions.
- Valid telemetry is persisted in PostgreSQL.
- Invalid messages and processing failures are observable.
- Duplicate delivery does not create duplicate logical records or anomaly events.
- Rule-based anomalies are persisted and made available through DashboardService.
- Cloud resources can be deployed reproducibly using Terraform.

## 8. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
- [ADR-001: Industrial Protocol and Edge-to-Cloud Communication](ADR-001-opcua-mqtt.md)
