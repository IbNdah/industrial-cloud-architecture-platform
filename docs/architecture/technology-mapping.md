# Technology Mapping

**Status:** Draft
**Phase:** S1 — Architecture Definition
**Version:** 0.1.0

## 1. Purpose

Map the logical architecture components to the selected technologies and identify implementation dependencies.
The mapping prioritizes reuse of existing Azure infrastructure patterns and avoids unnecessary services.

## 2. Technology Mapping

| Architecture Component | Selected Technology | Purpose | Status |
|---|---|---|---|
| Industrial assets | Simulated industrial assets | Generate motor, pump, conveyor and fan telemetry | Planned |
| PLC / SCADA | Logical simulation or existing industrial interface | Represent local control and supervision | To validate |
| Industrial protocol | OPC UA | Expose industrial measurements to authorized clients | Selected |
| Edge Gateway | Python 3.11 | Read, validate, normalize and forward telemetry | Selected |
| Edge packaging | Docker | Package and deploy the Edge Gateway | Selected |
| Local persistence | SQLite | Buffer telemetry during connectivity outages | Selected |
| Edge-to-cloud messaging | MQTT over TLS | Secure telemetry transport | Selected |
| Cloud ingestion | Azure IoT Hub | Authenticate Edge identities and ingest telemetry | Selected |
| Event processing | Azure Functions | Validate telemetry and evaluate anomaly rules | Selected |
| Operational database | Azure Database for PostgreSQL Flexible Server | Store telemetry, asset state and anomaly events | Selected |
| Application API | Python-based DashboardService | Expose asset status, trends and anomaly information | Planned |
| Visualization | Grafana | Display asset health, trends and alerts | Selected |
| Infrastructure as Code | Terraform | Provision cloud infrastructure reproducibly | Reuse |
| CI/CD | GitHub Actions | Validate code and automate deployment | Reuse |
| Monitoring | Azure Monitor / Application Insights | Observe cloud processing, errors and availability | Reuse |

## 3. Data Flow

1. Industrial assets generate measurements exposed through OPC UA.
2. The Edge Gateway reads the measurements and validates and normalizes the telemetry.
3. The Edge Gateway stores messages in SQLite when necessary and forwards them using MQTT over TLS.
4. Azure IoT Hub authenticates the Edge identity and ingests telemetry.
5. Azure Functions process telemetry and evaluate rule-based anomaly conditions.
6. Processed telemetry and anomaly events are persisted in PostgreSQL.
7. DashboardService exposes the information to Grafana.

The local control system must remain operational if cloud connectivity is unavailable. Buffered telemetry is forwarded after connectivity is restored.

## 4. Technology Decisions and Constraints

### 4.1 Azure IoT Hub

IoT Hub is the selected cloud ingestion service. A separate Event Hubs namespace is not included in the initial scope because it would add complexity without a demonstrated requirement.
Reconsider a separate event streaming service if independent consumers, additional throughput, or specific retention requirements justify it.

### 4.2 Azure Functions

Azure Functions provide event-driven processing without requiring a Kubernetes platform for this initial workload.

### 4.3 PostgreSQL

PostgreSQL is the primary database for this project. The schema must support asset identification, telemetry timestamps, historical measurements and anomaly events.
A dedicated time-series database may be evaluated later if measured workload requirements justify it.

### 4.4 Edge Gateway

The Edge Gateway runs as a Docker container. SQLite provides persistent local buffering; message identifiers support deduplication when messages are replayed.
The Edge Gateway does not implement remote PLC control.

### 4.5 Grafana

Grafana accesses operational information through DashboardService. Database credentials must not be embedded in dashboards or exposed to users.

## 5. Reuse of Existing Projects

| Existing Project | Reusable Capabilities |
|---|---|
| [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) | Terraform patterns, Azure baseline, security and governance controls |
| [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | IoT ingestion, Azure Functions, API patterns, Grafana, monitoring and CI/CD |

Reuse should be selective. Industrial OT requirements, Edge buffering and PostgreSQL data modeling remain specific to this project.

## 6. Deferred Technologies

The following technologies are excluded from the initial implementation unless a concrete requirement emerges:

- Kubernetes / AKS
- Apache Kafka
- Machine learning for predictive maintenance
- Data Lake / dedicated analytics platform
- Digital Twins services
- Dedicated time-series database

Rule-based anomaly detection is sufficient for the initial demonstrator. Machine learning can be considered after collecting representative data and defining measurable evaluation criteria.

## 7. Validation Items

Before implementation, validate:

- OPC UA server availability and telemetry model.
- Edge identity provisioning, credential rotation and revocation.
- MQTT/TLS connectivity and firewall rules.
- SQLite buffering limits, replay behavior and message deduplication.
- IoT Hub routing and Azure Functions integration.
- PostgreSQL private connectivity, authentication, backup and retention.
- DashboardService and Grafana connectivity.
- Terraform module compatibility with the existing cloud foundation.

## 8. Related Documents

- [Project Context](context.md)
- [High-Level Architecture](high-level-architecture.md)
- [OT Architecture](ot-architecture.md)
- [Security Architecture](security-architecture.md)
- [Requirements](requirements.md)
- [Gap Analysis](gap-analysis.md)
- [Architecture Decision Records](../adr/)
