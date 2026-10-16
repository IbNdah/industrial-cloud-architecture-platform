# ADR-006: Azure Functions vs AKS/Kubernetes

- **Status:** Accepted
- **Date:** 2026-10-16
- **Decision owners:** Industrial Cloud Architecture project
- **Scope:** Initial cloud ingestion and telemetry processing

## Context

The Industrial Asset Monitoring Platform must ingest telemetry from industrial assets, validate and process incoming messages, detect threshold-based anomalies, persist operational data, and expose information to a dashboard.
The initial workload is event-driven and has a limited operational scope. The architecture must remain reproducible, observable, secure, and suitable for a portfolio demonstrator that can later evolve toward production requirements.

Two deployment approaches were considered:

- Azure Functions for event-driven processing.
- Azure Kubernetes Service (AKS) for containerized workloads and orchestration.

## Decision

Use **Azure Functions** for the initial cloud-side telemetry processing.

The selected flow is:

1. Azure IoT Hub receives telemetry from the Edge Gateway.
2. Azure Functions process incoming messages.
3. The processing logic validates payloads and detects threshold-based anomalies.
4. Validated telemetry and relevant operational events are persisted in Azure Database for PostgreSQL Flexible Server.
5. DashboardService exposes the information required by Grafana.

The initial solution will not deploy AKS.

## Rationale

Azure Functions is preferred because it:

- Fits event-driven telemetry processing.
- Reduces infrastructure and cluster-management overhead.
- Integrates with Azure monitoring and identity capabilities.
- Supports independent deployment and testing of processing logic.
- Keeps the initial solution focused on industrial architecture, security, and operational reliability.
AKS would introduce additional responsibilities, including cluster lifecycle management, Kubernetes networking, workload scheduling, upgrades, and cluster-level security.

These capabilities are not justified by the initial workload.

## Consequences

### Positive

- Lower operational complexity and fewer infrastructure components.
- Faster implementation and simpler deployment.
- Clear separation between ingestion, processing, persistence, and presentation.
- Easier demonstration of Azure-native architecture patterns.

### Trade-offs

- Processing is coupled to the Azure Functions execution model and its hosting limits.
- Long-running or specialized workloads may require a different execution model.
- Function scaling, retries, timeouts, and database connection usage must be configured and monitored carefully.
- Delivery guarantees must be handled explicitly; successful message receipt alone does not prove that the database transaction has committed.

## Conditions for Reconsidering AKS

Reassess AKS only if measurable requirements justify the additional complexity, for example:

- Multiple long-running services require coordinated orchestration.
- Workloads need Kubernetes-specific scheduling or networking capabilities.
- Portability across several Kubernetes environments becomes a concrete requirement.
- Function execution constraints materially affect workload design.
- Operational capacity exists to manage Kubernetes securely throughout its lifecycle.

The presence of containers alone is not sufficient justification for AKS.

## Security and Reliability

- Use managed identities where supported to avoid long-lived credentials.
- Store secrets in Azure Key Vault when secrets are required.
- Apply least-privilege access to Azure resources and PostgreSQL.
- Configure retries and error handling deliberately.
- Make processing idempotent so duplicate deliveries do not create duplicate operational records.
- Monitor processing failures, latency, retries, and database connectivity.

## Alternatives Considered

| Option | Assessment |
|---|---|
| Azure Functions | Selected for the initial event-driven workload |
| AKS | Deferred until requirements justify cluster orchestration |
| Self-managed Kubernetes | Rejected for the initial scope because of operational overhead |
| Dedicated virtual machines | Not selected because they add host-management responsibilities without a clear initial benefit |

## Related Decisions

- ADR-002: Cloud Ingestion and Event Processing
- ADR-003: PostgreSQL Operational Database
- ADR-005: Edge Buffering and Message Delivery Semantics
- ADR-007: Docker for the Edge Gateway

## Review

Revisit this decision when workload characteristics, deployment constraints, availability targets, or operational requirements change materially.
