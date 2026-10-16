# Industrial Cloud Architecture Platform

## 🎯 Overview

An Azure-based industrial IoT reference implementation demonstrating secure OT-to-cloud integration for industrial asset monitoring.

The platform builds on an existing Azure IoT monitoring pipeline and adds industrial protocols, Edge integration, OT/IT security, and industrial asset modeling.

## 🏭 Business Use Case

**Smart Manufacturing Plant — Machine Health Monitoring**

The platform simulates industrial assets, collects telemetry, detects rule-based anomalies, and exposes machine-health information through a monitoring dashboard.

Initial simulated assets:
- **M-101 / M-102:** electric motors
- **P-101:** pump
- **C-101:** conveyor
- **F-101:** fan

## 🏗️ Architecture

```text
Industrial Assets → PLC → SCADA/HMI → OPC UA Server
                                      ↓
                          Docker Edge Gateway
                                      ↓
                           SQLite Persistent Buffer
                                      ↓ MQTT over TLS
                         Industrial DMZ / Firewall
                                      ↓
                              Azure IoT Hub
                                      ↓
                            Azure Functions
                                      ↓
                    Azure Database for PostgreSQL
                                      ↓
                         DashboardService API
                                      ↓
                                   Grafana
```

Key design principles:
- Local industrial control remains independent of cloud connectivity.
- No direct Cloud-to-PLC control path.
- Edge telemetry is buffered locally and replayed after reconnection.
- Delivery is at-least-once; stable message IDs and cloud-side deduplication handle duplicates.
- Infrastructure is managed with Terraform; CI/CD uses GitHub Actions.

## 🧩 Architecture Scope

- Industrial OT and Edge integration
- OPC UA and MQTT over TLS
- Azure IoT Hub and event-driven processing with Azure Functions
- PostgreSQL for operational telemetry and alarms
- DashboardService API and Grafana
- Industrial network segmentation and identity/security controls
- Azure Enterprise Landing Zone integration
- Infrastructure as Code with Terraform
- Monitoring and operational visibility with Azure Monitor / Application Insights

Machine-learning-based predictive maintenance, Kubernetes, and additional data platforms are outside the initial implementation scope. Initial anomaly detection uses configurable rules.

## ♻️ Reuse Strategy

The existing [EV Fleet Monitoring Platform](https://github.com/IbNdah/ev-fleet-monitoring-platform) is the technical baseline. Relevant cloud ingestion, processing, monitoring, and CI/CD patterns will be reused or adapted where appropriate.

The [Azure Enterprise Cloud Foundation](https://github.com/IbNdah/azure-enterprise-cloud-foundation) provides a reference for cloud governance and landing-zone practices.

The goal is to focus implementation effort on industrial-specific requirements rather than duplicate existing cloud foundations.

## 📌 Project Status

- [x] S0 — Project initialization
- [x] S1 — Architecture definition and gap review
- [ ] S2 — Industrial asset simulator and OPC UA server
- [ ] S3 — Industrial Edge Gateway and local buffering
- [ ] S4 — Cloud ingestion and Machine Health Monitoring
- [ ] S5 — Industrial security hardening and observability
- [ ] S6 — Landing Zone integration and portfolio documentation

## 🛠️ Technology Stack

- Microsoft Azure
- Python 3.11
- OPC UA / MQTT
- SQLite for Edge buffering
- Azure IoT Hub and Azure Functions
- Azure Database for PostgreSQL Flexible Server
- Docker
- Terraform
- GitHub Actions
- Grafana

## ⚠️ Scope and Deployment Status

This repository documents an evolving industrial reference implementation. Components and capabilities are added and validated incrementally. The solution is not certified or validated for direct production OT deployment and does not control real industrial equipment.
