# ADR-007: Docker for the Edge Gateway

- **Status:** Accepted
- **Date:** 2026-10-16
- **Decision owners:** Industrial Cloud Architecture project
- **Scope:** Packaging and deployment of the industrial Edge Gateway

## Context

The Edge Gateway connects the industrial OT environment to Azure. It reads telemetry from an OPC UA server, validates and normalizes data, maintains a persistent local queue, and publishes messages securely to Azure IoT Hub.
The gateway must be deployable in a controlled industrial environment and continue to support local buffering when cloud connectivity is unavailable.
Deployment must be repeatable and maintainable without introducing unnecessary orchestration infrastructure.

## Decision

Package the Edge Gateway as a **Docker container**.

For the initial demonstrator:

- Use Docker to build and run the Python-based Edge Gateway.
- Externalize environment-specific configuration.
- Keep credentials and certificates outside the container image.
- Persist the local SQLite queue using a Docker volume or an equivalent durable host-mounted storage location.
- Define resource limits and restart behavior appropriate to the target environment.
- Use versioned images and a controlled deployment process.

Kubernetes and Docker Swarm will not be introduced for the initial Edge deployment.

## Rationale

Docker provides:

- A reproducible runtime for the gateway and its dependencies.
- Separation between application packaging and the host operating system.
- Consistent development and deployment environments.
- A practical mechanism for versioning, updating, and rolling back gateway software.
- A manageable deployment model for a small number of industrial edge components.

The container is a packaging and runtime mechanism. It does not replace OT network segmentation, host hardening, identity management, or operational procedures.

## Deployment and Runtime Requirements

### Configuration

- Keep environment-specific settings outside the image.
- Do not bake credentials, private keys, or certificates into the image.
- Validate required configuration at startup.
- Separate development and production settings.

### Persistent Storage

- Store the SQLite queue on durable storage outside the container's writable layer.
- Preserve queued messages across container restarts and image upgrades.
- Define disk-space monitoring and queue-retention behavior.
- Do not delete or recreate the queue during routine container replacement.

### Security

- Run as a non-root user where practical.
- Use a minimal, maintained base image.
- Pin and review application dependencies.
- Scan images for known vulnerabilities.
- Avoid privileged containers and unnecessary host mounts.
- Restrict network access to required OT and cloud endpoints.
- Protect certificates and other credentials using host-level controls or an appropriate secrets mechanism.

### Reliability

- Configure an appropriate restart policy.
- Implement graceful shutdown so in-flight work and queued messages are handled safely.
- Ensure message replay is compatible with duplicate delivery.
- Expose health and connectivity information for operational monitoring.
- Keep local control and safety functions independent of the cloud gateway.

### Updates and Rollback

- Build immutable, versioned container images.
- Test new versions before deployment.
- Define a rollback procedure.
- Verify configuration compatibility and persistent-queue compatibility before upgrading.
- Maintain an inventory of deployed gateway versions.

## Consequences

### Positive

- Repeatable packaging and deployment.
- Reduced dependency drift between environments.
- Clear separation of application and host responsibilities.
- Straightforward local testing and troubleshooting.

### Trade-offs

- Docker host security and lifecycle remain operational responsibilities.
- Persistent storage must be managed explicitly.
- Container updates require controlled deployment and rollback procedures.
- Production use may require an industrial device-management or container-management platform, depending on fleet size and site requirements.

## Alternatives Considered

| Option | Assessment |
|---|---|
| Docker container | Selected for consistent packaging and manageable deployment |
| Direct Python installation on the host | Not selected because dependency and runtime management would be less reproducible |
| Kubernetes at the edge | Deferred because the initial scope does not justify orchestration overhead |
| Virtual machine per gateway | Possible in some environments, but not required for the initial demonstrator |

## Scope Boundaries

Docker does not provide industrial network segmentation by itself. The OT network, industrial DMZ, firewall rules, and cloud connectivity must be designed and enforced independently.

The Edge Gateway must not create a direct cloud-to-PLC control path. Local control remains within the OT environment.

The SQLite queue supports durable local buffering, while stable message identifiers and idempotent cloud processing address duplicate delivery during replay.

## Related Decisions

- ADR-001: Industrial Protocol and Edge-to-Cloud Communication
- ADR-004: Industrial Network Segmentation and Security Boundaries
- ADR-005: Edge Buffering and Message Delivery Semantics
- ADR-006: Azure Functions vs AKS/Kubernetes

## Review

Revisit this decision when the number of gateways, fleet-management requirements, hardware constraints, security policies, or site deployment model materially change.
