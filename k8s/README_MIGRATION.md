# Kubernetes Migration (K3d)

This directory contains the Kubernetes manifests for the backend microservices, migrated from Docker Compose to K3d (K3s in Docker).

## Prerequisites
- **K3d**: Installed via Winget (`winget install -e --id k3d.k3d`)
- **Docker**: Must be running.
- **Kubectl**: Installed via Docker Desktop or separately.

## Directory Structure
- `00-namespace.yaml`: Creates `backend` namespace.
- `01-redis.yaml`, `02-rabbitmq.yaml`: Infrastructure services.
- `03-*.yaml` to `08-*.yaml`: Backend microservices (Deployments + Services).
- `deploy_k3d.ps1`: Automation script to tag, import, and deploy everything.

## Quick Start
1. Ensure K3d cluster is running.
2. Build images: `docker compose build`
3. Run the deployment script: `.\deploy_k3d.ps1`

## Notes
- **Volume Mounts**: The `ai-knowledge-service` uses local volume mounts for large models/vector DB. The cluster must be created with the volume mount:
  ```powershell
  k3d cluster create backend-cluster --servers 1 --agents 0 --volume "d:\bridge\copy backend:/project@server:0"
  ```
- **Resources**: Traefik and Metrics Server are disabled to save RAM (optimized for 8GB system).
