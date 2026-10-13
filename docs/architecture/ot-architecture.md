# OT Architecture

**Status:** Draft — S1
**Version:** 0.1.0

## 1. Purpose

Define the industrial environment and the boundary between Operational Technology (OT), Industrial Edge, and the cloud.

The initial use case monitors industrial assets. Control functions remain within the industrial environment.

## 2. Industrial Environment

The demonstrator represents one industrial site with five monitored assets.

| Asset ID | Type | Criticality | Telemetry |
|---|---|---|---|
| M-101 | Electric motor | High | Temperature, vibration, current, RPM |
| M-102 | Electric motor | High | Temperature, vibration, current, RPM |
| P-101 | Pump | High | Pressure, temperature, vibration, flow |
| C-101 | Conveyor | Medium | Speed, current, vibration |
| F-101 | Fan | Medium | RPM, temperature, vibration |

Assets and telemetry are simulated. No connection to real production equipment is required for the initial implementation.

## 3. OT Components

| Component | Responsibility | Interface |
|---|---|---|
| Sensors / asset simulator | Generate equipment measurements | Simulated signals |
| PLC | Represent local equipment control | Industrial control interfaces |
| SCADA / HMI | Represent local supervision and operator visibility | Industrial interfaces |
| OPC UA Server | Expose equipment data to authorized clients | OPC UA |
| Industrial Edge Gateway | Read, validate, normalize, buffer, and forward telemetry | OPC UA, MQTT over TLS |

The initial implementation simulates the OPC UA data source. Integration with real PLCs or SCADA systems is outside the initial scope.

## 4. Logical Architecture

```text
Industrial Assets
       |
       v
      PLC
       |
       v
   SCADA / HMI
       |
       v
   OPC UA Server
       |
       | OPC UA
       v
 Industrial Edge Gateway
       |
       | MQTT over TLS
       v
 Industrial DMZ / Firewall
       |
       v
    Azure IoT Hub
```

The diagram shows the logical data path. The physical network topology and firewall rules must be defined for the target environment.

## 5. Edge Gateway Responsibilities

| Function | Expected behavior |
|---|---|
| Data acquisition | Read measurements from the OPC UA Server |
| Validation | Reject malformed or incomplete messages |
| Normalization | Convert source data into the agreed telemetry schema |
| Identification | Include asset ID, message ID, timestamp, and schema version |
| Local buffering | Persist messages in SQLite when cloud connectivity is unavailable |
| Forwarding | Publish telemetry to Azure IoT Hub through MQTT over TLS |
| Replay | Send queued messages after connectivity is restored |
| Monitoring | Expose connectivity, queue, and processing errors |

The delivery model is at-least-once. Cloud processing must handle duplicate messages using a stable message ID.

## 6. OT Continuity

| Situation | Required behavior |
|---|---|
| Cloud unavailable | Local control and supervision continue |
| Edge-to-cloud connection lost | Telemetry is buffered locally |
| Connection restored | Buffered messages are replayed |
| OPC UA source unavailable | Acquisition errors are recorded; unavailable measurements are not fabricated |
| Edge Gateway restarted | Persisted queued messages remain available |

The cloud is used for monitoring and analysis. It is not required for the basic operation of the industrial process.

## 7. Network Boundaries

| Zone | Main components | Principle |
|---|---|---|
| OT | Assets, PLCs, SCADA/HMI, OPC UA Server | Local control and supervision |
| Industrial DMZ | Controlled network boundary and permitted communication paths | Restrict traffic between OT and external networks |
| Cloud | IoT Hub, processing, database, API, Grafana | Telemetry processing and monitoring |

The Edge-to-cloud connection must use authenticated TLS. Network access must be restricted to explicitly authorized flows. There is no direct cloud-to-PLC control path.

The detailed identity, firewall, and access requirements are defined in `security-architecture.md` and the relevant Architecture Decision Records.

## 8. Initial Scope and Limitations

| Included | Deferred |
|---|---|
| Simulated industrial assets | Real production equipment integration |
| Simulated OPC UA Server | Vendor-specific PLC integration |
| Docker-packaged Edge Gateway | Kubernetes at the Edge |
| SQLite persistent buffer | Distributed Edge clustering |
| MQTT over TLS | Direct cloud-to-PLC control |
| Rule-based anomaly detection in the cloud | Machine-learning-based prediction |

## 9. Related Documents

- `context.md` — project purpose, objectives, and scope.
- `high-level-architecture.md` — end-to-end architecture.
- `security-architecture.md` — security requirements and controls.
- `../adr/ADR-001-opcua-mqtt.md` — industrial connectivity decision.
