
# Industrial Cloud Architecture Platform

## Overview

An industrial cloud architecture project demonstrating
secure OT-to-cloud integration using Microsoft Azure.

The project extends an existing Azure IoT monitoring
pipeline with industrial protocols, OT/IT security,
enterprise cloud governance, and industrial asset modeling.

## Business Use Case

Smart Manufacturing Plant — Machine Health Monitoring.

The platform collects simulated industrial machine
telemetry, processes operational events, and exposes
machine health information through a monitoring dashboard.

## Architecture Scope

- Industrial OT and Edge integration
- OPC UA and MQTT
- Azure IoT Hub and event-driven processing
- Azure Functions and Cosmos DB
- Industrial security and network segmentation
- Azure Enterprise Landing Zone integration
- Infrastructure as Code with Terraform
- Monitoring and operational visibility
- Digital Twin concepts

## Reuse Strategy

The existing EV Fleet Monitoring Platform is the
technical baseline.

Existing cloud ingestion, processing, persistence,
monitoring, and CI/CD components will be reused or
adapted where appropriate.

The objective is to focus implementation effort on
the genuine industrial architecture gaps.

## Project Status

- [x] Phase 0 — Project initialization
- [ ] S1 — Architecture and gap validation
- [ ] S2 — OPC UA and industrial asset simulation
- [ ] S3 — Industrial Edge integration
- [ ] S4 — Machine Health Monitoring
- [ ] S5 — Industrial security architecture
- [ ] S6 — Industrial Landing Zone integration

## Technology Stack

- Microsoft Azure
- Python 3.11
- MQTT / OPC UA
- Terraform
- Docker
- GitHub Actions
- Grafana

## Disclaimer

This is a learning and demonstration project.
It does not control real industrial equipment and
is not intended for production OT deployment.
