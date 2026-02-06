# Deploy to K3d

$CLUSTER_NAME = "backend-cluster"
$K3D_PATH = "C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages\k3d.k3d_Microsoft.Winget.Source_8wekyb3d8bbwe\k3d.exe"

Write-Host "Tagging images..."
# Explicitly tag images built by docker-compose to match our K8s manifests
docker tag backend-auth-service:latest auth-service:latest
docker tag backend-user-service:latest user-service:latest
docker tag backend-trainer-service:latest trainer-service:latest
docker tag backend-ai-service:latest ai-service:latest
docker tag backend-admin-service:latest admin-service:latest
docker tag backend-ai-knowledge-service:latest ai-knowledge-service:latest

Write-Host "Importing images to K3d cluster '$CLUSTER_NAME'..."
& $K3D_PATH image import auth-service:latest -c $CLUSTER_NAME
& $K3D_PATH image import user-service:latest -c $CLUSTER_NAME
& $K3D_PATH image import trainer-service:latest -c $CLUSTER_NAME
& $K3D_PATH image import ai-service:latest -c $CLUSTER_NAME
& $K3D_PATH image import admin-service:latest -c $CLUSTER_NAME
& $K3D_PATH image import ai-knowledge-service:latest -c $CLUSTER_NAME

Write-Host "Applying Kubernetes manifests..."
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/

Write-Host "Deployment complete! Checking pods..."
kubectl get pods -n backend
