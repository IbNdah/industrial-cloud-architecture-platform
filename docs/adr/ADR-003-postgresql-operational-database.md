# ADR-003: PostgreSQL as the Operational Database

**Status:** Accepted
**Date:** 2026-10-16
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.0.0

## 1. Context

The Industrial Asset Monitoring Platform must persist telemetry from industrial assets, maintain the latest known asset state, and store anomaly events for operational monitoring and historical analysis.
The database must support structured queries, reliable persistence, controlled access and integration with Azure Functions and DashboardService.
The initial workload is a demonstrator with simulated industrial assets. A dedicated time-series database is not justified until actual workload characteristics and requirements are known.

## 2. Decision

Azure Database for PostgreSQL Flexible Server is selected as the primary operational database.
It will store:

- **Asset information:** asset identifier, type, location or production area, and configured monitoring thresholds.
- **Telemetry:** asset identifier, message identifier, event timestamp, ingestion timestamp and validated measurements.
- **Latest asset state:** latest accepted measurements and derived operational status.
- **Anomaly events:** anomaly type, severity, detection timestamp, observed value, threshold and processing status.

The initial implementation will use a relational schema with explicit keys, constraints and indexes.

## 3. Data Model Principles

### 3.1 Asset Identity

Each asset must have a stable identifier, such as `M-101` or `P-101`.
Telemetry must reference a known asset. Unknown asset identifiers must be rejected or quarantined according to the validation policy.

### 3.2 Telemetry Identity and Deduplication

Each telemetry message must have a stable, unique message identifier generated at the Edge Gateway.
The database must enforce uniqueness for the relevant message identity so that retries and replay do not create duplicate logical telemetry records.
The deduplication key must be defined consistently across the Edge Gateway, Azure Functions and PostgreSQL schema.

### 3.3 Timestamps

Store at least:

- `event_timestamp`: when the measurement was observed at the source.
- `ingestion_timestamp`: when the cloud ingestion or processing layer received the message.

Use timezone-aware timestamps and a consistent UTC storage convention.
These timestamps support delay analysis, replay handling and historical queries.

### 3.4 Anomaly Events

Anomaly events must be stored separately from raw telemetry so that detection results can be queried and tracked independently.
Repeated processing of the same message must not create duplicate anomaly events for the same logical detection.

## 4. Alternatives Considered

| Alternative | Decision |
|---|---|
| Azure Cosmos DB | Not selected for this workload because relational queries and structured relationships are central to the initial design; it remains in use in the separate EV Fleet project |
| Dedicated time-series database | Deferred until measured query, ingestion or retention requirements justify it |
| Data Lake | Deferred because the initial workload does not require a separate analytical storage layer |
| Self-managed PostgreSQL on a VM | Not selected because it increases database administration and operational responsibility |
| Multiple databases for different data types | Rejected for the initial scope to avoid unnecessary operational complexity |

## 5. Consequences

### Positive

- Structured relational model for assets, telemetry and anomalies.
- SQL support for dashboard queries and historical analysis.
- Managed Azure database service.
- Transactional persistence and uniqueness constraints support idempotent processing.
- A straightforward migration path if specialized time-series capabilities become necessary.

### Trade-offs

- Database indexes, retention and query performance require validation.
- High ingestion rates may require batching and connection management.
- Historical telemetry growth must be monitored.
- Availability, backup, recovery and network configuration must be designed and tested.

## 6. Security and Operations

- Prefer private network connectivity where supported by the deployment architecture.
- Use managed identities or another supported secure authentication mechanism where applicable.
- Store credentials securely; never commit them to the repository.
- Apply least-privilege database roles.
- Define backup, recovery and retention policies before production deployment.
- Monitor connection limits, storage consumption, query latency and failed writes.
- Avoid exposing database credentials directly to Grafana; access operational data through DashboardService.

## 7. Verification Criteria

The decision is considered implemented when:

- PostgreSQL is provisioned reproducibly using Terraform.
- Asset, telemetry, latest-state and anomaly data can be persisted.
- Duplicate message identifiers cannot create duplicate logical telemetry records.
- Repeated processing cannot create duplicate logical anomaly events.
- Historical queries can retrieve measurements by asset and time range.
- Database connectivity is restricted to authorized application components.
- Backup and recovery procedures are documented and tested.
- Retention and indexing choices are documented and validated against the demonstrator workload.

## 8. Conditions for Reassessment

Reassess the database choice if measured workload results demonstrate that:

- Telemetry ingestion exceeds the selected database configuration's capacity.
- Historical time-series queries cannot meet defined latency targets.
- Data retention or storage growth becomes operationally costly.
- A dedicated time-series platform provides a measurable benefit that justifies its additional complexity.

## 9. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
- [ADR-001: Industrial Protocol and Edge-to-Cloud Communication](ADR-001-opcua-mqtt.md)
- [ADR-002: Cloud Ingestion and Event Processing](ADR-002-cloud-ingestion-processing.md)
