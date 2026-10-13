# Architecture Gap Analysis

**Status:** Draft — S1.3
**Version:** 0.1.0

## 1. Purpose

Identify which capabilities can be reused from the [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) and [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform), and which changes are required for industrial asset monitoring.

## 2. Capability Assessment

| Capability | Existing source | Assessment | Required action |
|---|---|---|---|
| Cloud governance and networking | [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) | Reuse | Integrate the workload with the existing foundation where applicable |
| Infrastructure as Code | [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) and [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse | Reuse Terraform conventions and modules where suitable |
| CI/CD and quality checks | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) / [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) | Reuse and adapt | Adjust pipelines to the new application and infrastructure |
| Telemetry simulation | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Modify | Replace vehicle and battery models with industrial assets and measurements |
| MQTT communication | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse and adapt | Retain MQTT for Edge-to-cloud telemetry transport |
| Azure IoT Hub | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse and adapt | Review device identity, message routing, and ingestion configuration |
| Azure Functions | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse and adapt | Implement industrial telemetry processing, alarm rules, and API endpoints |
| Data persistence | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) uses Cosmos DB | Change | Use PostgreSQL for the industrial asset and telemetry model |
| DashboardService API | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse and adapt | Expose industrial asset status, telemetry trends, and alarms |
| Grafana | [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse and adapt | Adapt dashboards and queries to the industrial API |
| Monitoring and application logs | [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) and [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) | Reuse and adapt | Cover Edge connectivity, message processing, queue status, and cloud failures |

## 3. Architecture Changes

### 3.1 Telemetry source

EV Fleet generates vehicle telemetry. The industrial platform must instead acquire measurements from an OPC UA source.

The initial implementation will use simulated industrial assets and a simulated OPC UA server. Integration with real PLCs is deferred.

### 3.2 Edge processing

The Edge Gateway must support:

- OPC UA data acquisition.
- Schema validation and normalization.
- Persistent local buffering with SQLite.
- Message replay after connectivity recovery.
- MQTT over TLS for cloud communication.

The existing MQTT patterns can be reused, but the industrial acquisition and resilience requirements need additional implementation.

### 3.3 Data persistence

The industrial workload will use PostgreSQL instead of reusing the Cosmos DB data model from EV Fleet.

The initial relational model will cover factories, assets, telemetry, and alarms. The existing EV Fleet project remains unchanged.

### 3.4 Cloud ingestion

Azure IoT Hub and Azure Functions remain the preferred ingestion and processing components.

The IoT Hub built-in endpoint is Event Hubs-compatible. A separate Event Hubs namespace will not be introduced unless independent consumers, retention, or throughput requirements justify it.

### 3.5 Industrial network boundaries

The architecture must explicitly distinguish the OT environment, Industrial DMZ, and cloud.

Cloud connectivity is used for telemetry and monitoring. The initial design does not provide a direct cloud-to-PLC control path.

## 4. Capabilities Deferred

| Capability | Decision | Reason |
|---|---|---|
| AKS / Kubernetes | Defer | Not required for the initial workload |
| Kafka | Defer | No demonstrated requirement for an additional streaming platform |
| Separate Event Hubs namespace | Defer | IoT Hub provides an Event Hubs-compatible built-in endpoint |
| Data Lake | Defer | Initial scope is asset monitoring, not large-scale historical analytics |
| Machine learning | Defer | Rule-based anomaly detection is sufficient for the demonstrator |
| Azure Digital Twins | Defer | A dedicated digital-twin service is not needed to validate the initial use case |
| Dedicated time-series database | Defer | Start with PostgreSQL and reassess using measured workload characteristics |
| Edge Kubernetes or clustering | Defer | A single Docker-packaged gateway is sufficient for the initial demonstrator |

## 5. Key Risks and Dependencies

| Item | Risk or dependency | Follow-up |
|---|---|---|
| PostgreSQL networking | Private connectivity depends on the selected Azure network design | Validate Terraform support, DNS, and application connectivity |
| Edge identity | Credentials must be identifiable, protected, and revocable | Define provisioning and rotation procedures |
| Store-and-forward | Outages can create queue growth and duplicate deliveries | Define queue limits, replay behavior, and message deduplication |
| IoT Hub integration | Routing and Function trigger configuration must match the ingestion design | Validate end-to-end message delivery |
| Grafana connectivity | Dashboard access depends on the hosting and network model | Validate DashboardService authentication and connectivity |
| Foundation integration | Existing modules and outputs may not cover all workload requirements | Inspect and reuse only suitable modules |

## 6. Outcome

The industrial platform will reuse the existing cloud and IoT foundations while adding the capabilities specific to industrial environments.

The main additions are OPC UA acquisition, an industrial asset model, persistent Edge buffering, OT network segmentation, and PostgreSQL persistence.

Implementation should proceed only after the corresponding requirements and Architecture Decision Records have been reviewed.

## 7. Related Documents and Projects

- `context.md` — project purpose and scope.
- `ot-architecture.md` — industrial components and data flows.
- `requirements.md` — functional and non-functional requirements.
- `technology-mapping.md` — Azure service mapping.
- `../adr/` — architecture decisions.
- [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) — cloud foundation and governance baseline.
- [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) — reusable IoT ingestion, telemetry processing, and monitoring patterns.
