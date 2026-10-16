# ADR-004: Industrial Network Segmentation and Security Boundaries

**Status:** Accepted
**Date:** 2026-10-16
**Decision Owners:** Industrial Cloud Architecture Project
**Version:** 1.0.0

## 1. Context

The Industrial Asset Monitoring Platform connects industrial equipment to cloud services for telemetry processing, anomaly detection and visualization.
Industrial control systems have different availability and security requirements from enterprise IT and cloud workloads. A compromise or outage in the cloud must not directly affect local industrial control.
The architecture therefore requires explicit security boundaries, restricted communication paths and a clear separation between monitoring and control.

## 2. Decision

The architecture is logically divided into three security zones:
1. **OT Zone:** industrial assets, PLCs, SCADA/HMI and the OPC UA Server.
2. **Industrial DMZ:** the Edge Gateway and the controlled boundary for communication between OT and external networks.
3. **Cloud Zone:** Azure IoT Hub, Azure Functions, PostgreSQL, DashboardService, Grafana and monitoring services.

The exact physical placement of the Edge Gateway depends on the deployment environment. The gateway must not create an unrestricted bridge between OT and cloud networks.
Network rules must permit only the communication required by the monitoring use case.

## 3. Zone Responsibilities

### 3.1 OT Zone

Contains the industrial assets and local control components.

- PLCs execute local control logic.
- SCADA/HMI supports local supervision.
- The OPC UA Server exposes authorized industrial measurements.
- Local control remains operational during cloud outages.
- Cloud services must not initiate direct connections to PLCs.

### 3.2 Industrial DMZ

Hosts or protects the Edge Gateway and mediates industrial data transfer.
- The Edge Gateway reads approved measurements from the OPC UA Server.
- The gateway validates and normalizes telemetry.
- Telemetry is buffered locally in SQLite during connectivity outages.
- Cloud communication uses authenticated MQTT over TLS.
- Firewall rules restrict both destinations and permitted traffic.
- The gateway must not forward arbitrary traffic between OT and cloud networks.
The Edge Gateway's precise placement must be validated against the target site's network design and security policy.

### 3.3 Cloud Zone

Hosts managed Azure services for ingestion, processing, persistence and visualization.
- IoT Hub authenticates device connections and receives telemetry.
- Azure Functions process messages and evaluate anomaly rules.
- PostgreSQL stores telemetry and anomaly data.
- DashboardService exposes authorized application queries.
- Grafana visualizes operational information.
- Azure Monitor and Application Insights provide observability.

Cloud services must not have a direct control path to PLCs.

## 4. Permitted Communication Flows

| Source | Destination | Purpose | Policy |
|---|---|---|---|
| Industrial assets / PLCs | OPC UA Server | Expose industrial measurements | Restricted to required industrial communication |
| Edge Gateway | OPC UA Server | Read authorized telemetry | Allow only required endpoints and operations |
| Edge Gateway | Azure IoT Hub | Publish telemetry over MQTT/TLS | Outbound, authenticated and restricted |
| IoT Hub | Azure Functions | Deliver telemetry for processing | Managed cloud integration |
| Azure Functions | PostgreSQL | Persist validated telemetry and anomalies | Authorized application access only |
| DashboardService | PostgreSQL | Query operational data | Least-privilege database access |
| Grafana | DashboardService | Retrieve dashboard information | Authenticated API access |
| Cloud services | PLCs | Direct control or unrestricted access | **Prohibited** |

The actual network ports, DNS dependencies and firewall rules must be documented and tested during implementation.

## 5. Security Controls

- Separate OT, DMZ and cloud trust boundaries.
- Use default-deny firewall policies where practical.
- Allow only explicitly required source-destination flows.
- Require TLS and device authentication for Edge-to-cloud communication.
- Use unique device identities and support credential revocation.
- Apply least privilege to cloud identities and database access.
- Prevent credentials from being stored in source code or container images.
- Log relevant connection failures, authentication errors and processing failures.
- Monitor Edge connectivity and local buffer growth.
- Keep local control independent of cloud availability.

## 6. Alternatives Considered

| Alternative | Decision |
|---|---|
| Direct cloud-to-PLC connectivity | Rejected because it increases OT exposure and creates an unnecessary control path |
| Flat network without security zones | Rejected because it weakens isolation and makes traffic control difficult |
| Unrestricted dual-homed Edge Gateway | Rejected because the gateway must not become an uncontrolled bridge |
| Fully isolated OT with no telemetry export | Not selected because the monitoring use case requires controlled outbound telemetry |
| Separate physical DMZ infrastructure for the demonstrator | To be determined by the deployment environment; logical separation is required, while physical implementation may vary |

## 7. Consequences

### Positive

- Clear separation of industrial control and cloud monitoring.
- Reduced attack surface and restricted communication paths.
- Better alignment with industrial security principles.
- Cloud outages do not directly interrupt local control.
- Network rules can be reviewed against explicit data flows.

### Trade-offs

- Firewall and routing configuration requires environment-specific validation.
- Edge Gateway placement must be agreed with OT and security stakeholders.
- Certificates, identities and network dependencies require operational management.
- A simulated environment cannot fully prove the security of a production OT deployment.

## 8. Verification Criteria

The decision is considered implemented when:

- The OT, Industrial DMZ and Cloud zones are documented.
- Each required communication flow has a defined source, destination and purpose.
- Firewall rules permit only approved traffic.
- The Edge Gateway can read authorized OPC UA measurements.
- The Edge Gateway can publish telemetry to IoT Hub over authenticated TLS.
- Cloud components cannot establish direct connections to PLCs.
- A cloud connectivity outage does not interrupt local control.
- Edge buffering and replay operate after connectivity is restored.
- Connection failures and authentication errors are observable.
- The final network implementation is reviewed against the target environment's security policy.

## 9. Related Documents

- [High-Level Architecture](../architecture/high-level-architecture.md)
- [OT Architecture](../architecture/ot-architecture.md)
- [Security Architecture](../architecture/security-architecture.md)
- [Requirements](../architecture/requirements.md)
- [Technology Mapping](../architecture/technology-mapping.md)
- [ADR-001: Industrial Protocol and Edge-to-Cloud Communication](ADR-001-opcua-mqtt.md)
