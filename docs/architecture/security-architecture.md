# Security Architecture

**Status:** Draft — S1
**Version:** 0.1.0

## 1. Purpose
git add docs/architecture/security-architecture.md
git commit -m "docs: define industrial security architecture"
git push
Define the security boundaries and minimum controls for collecting industrial telemetry and forwarding it to Azure.

The initial implementation uses simulated industrial equipment. Production deployment requires an environment-specific security assessment.

## 2. Security Zones

| Zone | Components | Security objective |
|---|---|---|
| OT | Assets, PLCs, SCADA/HMI, OPC UA Server | Protect local control and limit access to industrial systems |
| Industrial DMZ | Firewall and controlled communication paths | Restrict traffic between OT and external networks |
| Edge | Industrial Edge Gateway and local SQLite buffer | Protect device identity, data, and local processing |
| Azure | IoT Hub, Functions, PostgreSQL, DashboardService, Grafana | Authenticate access and restrict service communication |

## 3. Required Controls

| ID | Control | Implementation approach |
|---|---|---|
| SEC-01 | Network segmentation | Separate OT, Industrial DMZ, and cloud communication paths |
| SEC-02 | No direct cloud-to-PLC control path | Permit telemetry flows only; do not expose PLC control interfaces to Azure |
| SEC-03 | Encrypted Edge-to-cloud communication | Use MQTT over authenticated TLS |
| SEC-04 | Identifiable Edge identity | Assign a distinct identity to each gateway |
| SEC-05 | Revocable access | Provide a procedure to disable or revoke a gateway identity |
| SEC-06 | Least privilege | Grant each identity only the permissions required for its role |
| SEC-07 | Secret protection | Do not store credentials in source control or container images |
| SEC-08 | Database isolation | Avoid public PostgreSQL access; prefer private connectivity |
| SEC-09 | Application access control | Protect API and dashboard access using appropriate authentication and authorization |
| SEC-10 | Security monitoring | Record authentication failures, connection errors, and relevant application events |

## 4. Communication Rules

| Source | Destination | Protocol | Rule |
|---|---|---|---|
| Edge Gateway | OPC UA Server | OPC UA | Allow only the required read access |
| Edge Gateway | Azure IoT Hub | MQTT over TLS | Outbound authenticated telemetry connection |
| Azure Functions | PostgreSQL | PostgreSQL protocol over TLS | Allow only the required application connection |
| Grafana | DashboardService API | HTTPS | Authenticated access according to the hosting model |
| Azure services | PLCs | None | No direct cloud-to-PLC control path |

Exact ports, firewall rules, DNS requirements, and routing must be defined during deployment design.

## 5. Identity and Credentials

- Use a distinct identity for each Edge Gateway.
- Store credentials outside source code and container images.
- Define credential provisioning, rotation, revocation, and recovery procedures.
- Use Azure managed identities for supported Azure-to-Azure access where practical.
- Apply role-based access control to deployment and operational resources.
- Do not assume that a managed identity can authenticate every service connection; validate the selected PostgreSQL and IoT configurations.

## 6. Edge and Container Security

| Area | Minimum requirement |
|---|---|
| Container image | Use a controlled base image and pinned dependencies |
| Runtime privileges | Run without unnecessary privileges |
| Configuration | Inject environment-specific configuration at deployment |
| Local buffer | Restrict access to the SQLite database and queued telemetry |
| Updates | Version images and document rollback |
| Logging | Avoid logging credentials or sensitive connection details |

Docker packages the Edge Gateway but does not, by itself, provide network segmentation, secure provisioning, high availability, or secure updates.

## 7. Data Protection

- Validate telemetry before processing.
- Associate messages with a known asset and identifiable source.
- Use a stable message ID to handle duplicate delivery.
- Restrict database access to authorized application identities or credentials.
- Define retention and backup requirements before production deployment.
- Avoid storing unnecessary personal or sensitive information in telemetry.

## 8. Monitoring and Incident Handling

The platform should record:

- Failed authentication and connection attempts.
- Edge-to-cloud connectivity changes.
- Local queue growth and replay failures.
- Invalid telemetry and processing errors.
- Database connection failures.
- Changes to identities and access permissions where supported.

Operational procedures must explain how to revoke a compromised Edge identity, restore connectivity, and recover buffered telemetry.

## 9. Production Considerations

The following items require additional validation before connection to a real industrial environment:

- OT security assessment and approved network flows.
- Firewall configuration and ownership.
- Edge device hardening and secure provisioning.
- Certificate or credential lifecycle management.
- Private connectivity and DNS for Azure services.
- Backup, recovery, retention, and incident response procedures.
- Applicable organizational and industrial security requirements.

## 10. Related Documents

- `context.md` — project purpose and scope.
- `ot-architecture.md` — industrial components and communication flows.
- `requirements.md` — architecture requirements.
- `high-level-architecture.md` — end-to-end architecture.
- `../adr/ADR-001-opcua-mqtt.md` — industrial connectivity decision.
- `../adr/ADR-004-network-segmentation.md` — network segmentation decision.
