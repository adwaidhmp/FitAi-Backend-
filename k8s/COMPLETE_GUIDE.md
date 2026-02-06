# Complete Guide: Local Kubernetes (K3d) Setup

## 1. Executive Summary
We have successfully migrated the backend infrastructure from a resource-heavy **Minikube** VM to a lightweight **K3d** (Kubernetes in Docker) cluster. This setup runs actual Kubernetes nodes as Docker containers, consuming significantly less RAM (~500MB vs 2GB+) while providing a production-identical API.

### Key Components
- **Cluster**: A single-node K3d cluster named `backend-cluster`.
- **Orchestration**: Standard Kubernetes manifests (`Deployment`, `Service`, `Secret`).
- **Automation**: PowerShell scripts for one-click deployment and access.

---

## 2. Architecture Overview

### How it Works
1.  **Code to Image**: You build Docker images locally (`docker compose build`).
2.  **Image Import**: The `deploy_k3d.ps1` script tags these images and "pushes" them directly into the K3d cluster's internal registry.
3.  **Deployment**: Kubernetes schedules **Pods** (containers) based on the manifests in the `k8s/` folder.
4.  **Access**: The `start_app.ps1` script creates secure tunnels (`port-forward`) from your `localhost` to the internal ClusterIP services.

### Service Map
| Service | Local Port | Internal K8s Port | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `:8000` | `:8000` | Authentication & User Management |
| **User** | `:8001` | `:8000` | User Profile & Logic |
| **Trainer** | `:8002` | `:8000` | Trainer Logic |
| **Admin** | `:8003` | `:8000` | Admin Dashboard Backend |
| **AI** | `:8004` | `:8000` | AI Processing |
| **Knowledge** | `:8005` | `:8000` | Vector DB & RAG |
| **Redis** | - | `:6379` | Caching & Celery Broker |
| **RabbitMQ** | - | `:5672` | Event Bus |

---

## 3. Understanding the Docker Containers
You will see **two** containers running in Docker Desktop. This is normal!

1.  **`k3d-backend-cluster-server-0`**:
    - **What is it?**: This IS your Kubernetes Cluster.
    - **What it does**: It runs the "Control Plane" (API Server) AND your "Workloads" (Pod, Auth Service, User Service). Since we optimized for 8GB RAM, we squashed everything into this one container.

2.  **`k3d-backend-cluster-serverlb`**:
    - **What is it?**: The Load Balancer / Proxy.
    - **What it does**: It sits in front of the server. When you run `kubectl` commands, they hit this load balancer first, which forwards them to the server. It handles the networking magic so you can talk to the cluster from Windows.

---

## 4. How to Use (Step-by-Step)

### Step 1: Make Changes & Build
When you update code, rebuild the images:
```powershell
docker compose build
```

### Step 2: Deploy Updates
Run the deployment script. It handles everything (tagging, importing, applying manifests):
```powershell
.\k8s\deploy_k3d.ps1
```
*Wait for the script to finish and for pods to initialize.*

### Step 3: Start Access
To access the services from your browser or Postman/Frontend, start the port forwarding:
```powershell
.\k8s\start_app.ps1
```
*Keep this terminal window open.*

---

## 4. How to Test
You can verified the system is working by hitting the health endpoints:

**PowerShell:**
```powershell
curl -I http://localhost:8001/  # User Service
curl -I http://localhost:8000/  # Auth Service
```
If you get a `200 OK` or `404 Not Found` (from Django), the server is reachable!

---

## 5. Frontend Integration
**Good News:** You do NOT need to change any frontend code!

We designed the `start_app.ps1` script to match your original `docker-compose.yml` ports exactly:
- **Auth API**: `http://localhost:8000`
- **User API**: `http://localhost:8001`
- **Trainer API**: `http://localhost:8002`
- **Admin API**: `http://localhost:8003`
- **AI API**: `http://localhost:8004`
- **AI Knowledge**: `http://localhost:8005`

If your frontend (.env or hardcoded URLs) points to these addresses, it will work seamlessly with the new Kubernetes cluster.

---

## 6. Troubleshooting Guide

### Issue: Pods are "Pending" or "CrashLoopBackOff"
Check the status:
```powershell
kubectl get pods -n backend
```

### Issue: "CrashLoopBackOff"
This usually means a code error or missing secret. Check the logs:
```powershell
kubectl logs deployment/user-service -n backend
```

### Issue: "Pending" for a long time
The cluster might be waiting for the image import to finish.
1. Check events: `kubectl describe pod <pod-name> -n backend`
2. Ensure you ran `deploy_k3d.ps1` successfully.

---

## 7. How to Stop (Save RAM)

### Option A: Pause (Recommended)
This stops the containers but keeps your data and state.
```powershell
k3d cluster stop backend-cluster
```
**To Resume:**
```powershell
k3d cluster start backend-cluster
```

### Option B: Destroy (Reset)
This deletes everything. Use this if you want to start fresh.
```powershell
k3d cluster delete backend-cluster
```

### Stopping Access
To stop the `start_app.ps1` (port forwarding), simply go to that terminal window and press `Ctrl+C`.

---

## 8. Path to AWS Production
Everything we built here is compatible with AWS Elastic Kubernetes Service (EKS).

**Transition Plan:**
1.  **Registry**: Instead of `deploy_k3d.ps1` importing images locally, you will `docker push` images to **AWS ECR**.
2.  **Manifests**: Update `image: user-service` locally to `image: <aws-account-id>.dkr.ecr.region.amazonaws.com/user-service` in the YAML files.
3.  **Secrets**: Use **AWS Secrets Manager** or apply the `00-secret.yaml` manually to EKS (carefully!).
4.  **Ingress**: Replace `start_app.ps1` (port-forwarding) with a real **AWS Load Balancer** by changing `Service` type to `LoadBalancer`.

You are effectively running a "Cloud-in-a-Box" now!
