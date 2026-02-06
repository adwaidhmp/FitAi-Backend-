# Start Port Forwarding for All Services
# Maps K3d services to Localhost ports (matching Docker Compose)

Write-Host "Starting Port Forwarding..."

# Helper function to start port-forward as a background job/process
function Start-Forward {
    param($Service, $LocalPort, $ContainerPort)
    Write-Host "Forwarding $Service ($ContainerPort) -> localhost:$LocalPort"
    # Using Start-Process to run in separate windows/background so they don't block this shell
    Start-Process kubectl -ArgumentList "port-forward svc/$Service ${LocalPort}:${ContainerPort} -n backend" -NoNewWindow
}

Start-Forward -Service "auth-service"         -LocalPort 8000 -ContainerPort 8000
Start-Forward -Service "user-service"         -LocalPort 8001 -ContainerPort 8000
Start-Forward -Service "trainer-service"      -LocalPort 8002 -ContainerPort 8000
Start-Forward -Service "admin-service"        -LocalPort 8003 -ContainerPort 8000
Start-Forward -Service "ai-service"           -LocalPort 8004 -ContainerPort 8000
Start-Forward -Service "ai-knowledge-service" -LocalPort 8005 -ContainerPort 8000

Write-Host "All port-forwards initiated. Processes are running in background."
Write-Host "Press Ctrl+C in this terminal to stop the script (if running interactively) or manually kill kubectl processes to stop."
