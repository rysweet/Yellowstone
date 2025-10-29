# Yellowstone Deployment Quick Start Guide

Complete step-by-step guide for deploying Yellowstone in all environments.

## Environment Setup

### Local Development (Docker)

#### 1. Prerequisites

```bash
# Verify Docker installation
docker --version
docker-compose --version

# Clone and navigate
cd /home/azureuser/src/Yellowstone
```

#### 2. Configure Environment

```bash
# Copy environment template
cp deployment/.env.example deployment/.env

# Edit with your values
nano deployment/.env

# Key values to update:
# - CLAUDE_API_KEY
# - AZURE_SUBSCRIPTION_ID
# - Database passwords
```

#### 3. Start Services

```bash
# Navigate to deployment directory
cd deployment

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME              STATUS      PORTS
# yellowstone-api   Up          0.0.0.0:8000->8000/tcp
# postgres          Up          0.0.0.0:5432->5432/tcp
# redis             Up          0.0.0.0:6379->6379/tcp
# prometheus        Up          0.0.0.0:9090->9090/tcp
# grafana           Up          0.0.0.0:3000->3000/tcp
```

#### 4. Access Services

```bash
# API Health Check
curl http://localhost:8000/health

# Grafana Dashboard
# URL: http://localhost:3000
# Username: admin
# Password: admin

# Prometheus
# URL: http://localhost:9090

# Database (psql)
psql -h localhost -p 5432 -U yellowstone -d yellowstone
```

#### 5. Verify Database

```bash
# Connect to database
docker-compose exec postgres psql -U yellowstone -d yellowstone

# List tables
\dt audit.*
\dt metrics.*
\dt queries.*

# Check audit logs table exists
\d audit.audit_logs

# Exit
\q
```

#### 6. View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs yellowstone-api
docker-compose logs postgres

# Follow logs
docker-compose logs -f
```

#### 7. Cleanup

```bash
# Stop services (keep data)
docker-compose stop

# Stop and remove services
docker-compose down

# Complete cleanup (remove volumes)
docker-compose down -v
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install tools
# - kubectl: https://kubernetes.io/docs/tasks/tools/
# - helm: https://helm.sh/docs/intro/install/

# Verify installation
kubectl version --client
helm version

# Get cluster context
kubectl config get-contexts
kubectl config current-context
```

### Deployment Steps

#### 1. Create Namespace

```bash
./scripts/deploy.sh kubernetes create-namespace yellowstone

# Verify
kubectl get namespace yellowstone
kubectl get namespace -L name
```

#### 2. Create Secrets

```bash
# Set your secret values
kubectl create secret generic yellowstone-secrets \
  --from-literal=database_user=psqladmin \
  --from-literal=database_password=YourSecurePassword123! \
  --from-literal=redis_password=YourSecureRedisPassword123! \
  --from-literal=claude_api_key=YOUR-CLAUDE-API-KEY \
  -n yellowstone

# Verify secret created
kubectl get secrets -n yellowstone
kubectl describe secret yellowstone-secrets -n yellowstone
```

#### 3. Apply Configuration

```bash
# Apply ConfigMaps
kubectl apply -f kubernetes/configmap.yaml

# Verify configuration
kubectl get configmaps -n yellowstone
kubectl describe configmap yellowstone-config -n yellowstone
```

#### 4. Deploy Application

```bash
# Deploy using script
./scripts/deploy.sh kubernetes deploy yellowstone

# Or manually
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml

# Monitor rollout
kubectl rollout status deployment/yellowstone-api -n yellowstone

# Watch pods starting
kubectl get pods -n yellowstone --watch
```

#### 5. Verify Deployment

```bash
# Check deployment status
kubectl get deployment -n yellowstone
kubectl get pods -n yellowstone

# Check service
kubectl get svc -n yellowstone

# Get service details
kubectl describe svc yellowstone-api -n yellowstone

# Port forward to test
kubectl port-forward -n yellowstone svc/yellowstone-api 8000:8000 &

# Test API
curl http://localhost:8000/health

# Kill port forward
kill %1
```

#### 6. View Logs

```bash
# Real-time logs from deployment
kubectl logs -f deployment/yellowstone-api -n yellowstone

# Logs from specific pod
kubectl logs -f <pod-name> -n yellowstone

# Logs from all pods
kubectl logs -f deployment/yellowstone-api --all-containers=true -n yellowstone
```

#### 7. Debug Issues

```bash
# Describe pod for events
kubectl describe pod <pod-name> -n yellowstone

# Execute into pod
kubectl exec -it <pod-name> -n yellowstone -- /bin/bash

# Check resource usage
kubectl top pods -n yellowstone
kubectl top nodes

# View events
kubectl get events -n yellowstone --sort-by='.lastTimestamp'

# Check pod conditions
kubectl get pod <pod-name> -n yellowstone -o yaml | grep conditions
```

#### 8. Scaling

```bash
# Manual scale
kubectl scale deployment yellowstone-api --replicas=5 -n yellowstone

# View HPA status
kubectl get hpa -n yellowstone
kubectl watch hpa yellowstone-api-hpa -n yellowstone
```

#### 9. Cleanup

```bash
# Delete deployment
kubectl delete deployment yellowstone-api -n yellowstone
kubectl delete svc yellowstone-api -n yellowstone

# Delete namespace (removes everything)
kubectl delete namespace yellowstone
```

---

## Azure Cloud Deployment

### Prerequisites

```bash
# Install Azure CLI
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
# Windows: https://aka.ms/installazurecliwindows

# Verify installation
az version
az bicep --version

# Authenticate
az login

# Set subscription
az account set --subscription <subscription-id>

# Verify resource group exists
az group show --name Yellowstone
# Or create it
az group create --name Yellowstone --location eastus
```

### Deployment Steps

#### 1. Validate Templates

```bash
# Validate main infrastructure template
az bicep build --file azure/bicep/main.bicep

# Validate sentinel template
az bicep build --file azure/bicep/sentinel.bicep

# Should output compiled JSON without errors
```

#### 2. Deploy Infrastructure

```bash
# Deploy to Yellowstone resource group
az deployment group create \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --template-file azure/bicep/main.bicep \
  --parameters azure/bicep/parameters.prod.json

# Or use script
./scripts/deploy.sh azure deploy-infra prod Yellowstone

# Monitor deployment
az deployment group show \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --query "properties.provisioningState"
```

#### 3. Deploy Sentinel Configuration

```bash
# Get Log Analytics workspace ID from deployment outputs
WORKSPACE_ID=$(az deployment group show \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --query properties.outputs.logAnalyticsId.value -o tsv)

echo "Workspace ID: $WORKSPACE_ID"

# Deploy Sentinel setup
./scripts/deploy.sh azure deploy-sentinel prod Yellowstone

# Or manually
az deployment group create \
  --name yellowstone-sentinel \
  --resource-group Yellowstone \
  --template-file azure/bicep/sentinel.bicep \
  --parameters logAnalyticsWorkspaceId="$WORKSPACE_ID" \
             environment=prod
```

#### 4. Verify Resources

```bash
# List all resources in Yellowstone group
az resource list --resource-group Yellowstone -o table

# Check specific resources
az keyvault list --resource-group Yellowstone
az acr list --resource-group Yellowstone
az postgres server list --resource-group Yellowstone
az cache list --resource-group Yellowstone
```

#### 5. Configure Key Vault

```bash
# Get Key Vault name
KV_NAME=$(az keyvault list --resource-group Yellowstone \
  --query '[0].name' -o tsv)

echo "Key Vault: $KV_NAME"

# Store secrets
az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name database-password \
  --value 'YourSecurePassword123!'

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name claude-api-key \
  --value 'YOUR-CLAUDE-API-KEY'

# List secrets
az keyvault secret list --vault-name "$KV_NAME"

# Retrieve secret
az keyvault secret show \
  --vault-name "$KV_NAME" \
  --name database-password
```

#### 6. Build Container Image

```bash
# Get ACR name
ACR_NAME=$(az acr list --resource-group Yellowstone \
  --query '[0].name' -o tsv)

echo "Registry: $ACR_NAME.azurecr.io"

# Login to ACR
az acr login --name "$ACR_NAME"

# Build image
az acr build \
  --registry "$ACR_NAME" \
  --image yellowstone:latest \
  --image yellowstone:v1.0 \
  --file deployment/Dockerfile \
  .

# List images
az acr repository list --name "$ACR_NAME"

# Show tags
az acr repository show-tags \
  --name "$ACR_NAME" \
  --repository yellowstone
```

#### 7. Monitor Deployment

```bash
# View Log Analytics workspace
LA_ID=$(az deployment group show \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --query properties.outputs.logAnalyticsId.value -o tsv)

# Query logs
az monitor log-analytics query \
  --workspace "$LA_ID" \
  --analytics-query "AzureActivity | take 10"

# View alerts
az monitor metrics alert list --resource-group Yellowstone

# Check Application Insights
az resource show \
  --resource-group Yellowstone \
  --resource-type "Microsoft.Insights/components" \
  --query name -o tsv
```

#### 8. Cleanup (Destructive)

```bash
# Warning: This deletes all resources
./scripts/deploy.sh azure cleanup prod Yellowstone

# Or manually
az group delete --name Yellowstone --yes

# Verify deletion
az group show --name Yellowstone  # Should fail
```

---

## Post-Deployment Verification

### All Environments

```bash
# 1. Health Check
curl -v http://<yellowstone-url>/health

# Expected response:
# HTTP/1.1 200 OK
# {"status": "healthy"}

# 2. Database connectivity
# Verify audit logging is working
# Check query_history table has entries

# 3. Monitor metrics
# Check Prometheus for metrics collection
# Verify Grafana dashboards are updated

# 4. Test query translation
# Submit a Cypher query to the API
# Verify it translates to KQL successfully
```

### Docker Specific

```bash
# Access container
docker-compose exec yellowstone-api /bin/bash

# Check application logs inside container
cat /app/logs/application.log

# Verify configuration
env | grep YELLOWSTONE
```

### Kubernetes Specific

```bash
# Pod shell access
kubectl exec -it <pod-name> -n yellowstone -- /bin/bash

# View pod environment
kubectl exec <pod-name> -n yellowstone -- env | grep YELLOWSTONE

# Check mounted volumes
kubectl exec <pod-name> -n yellowstone -- ls -la /app
```

### Azure Specific

```bash
# Check private endpoints are configured
az network private-endpoint list --resource-group Yellowstone

# Verify no public IPs
az network public-ip list --resource-group Yellowstone

# Check private DNS resolution
# From within VNet, ping service FQDNs
nslookup <service>.vaultcore.azure.net
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Pod pending | Check resource requests, node capacity |
| Connection refused | Verify service is running, check firewall rules |
| Database error | Check connection string, credentials in secrets |
| High memory usage | Check pod limits, review application logs |
| Slow queries | Check indices, analyze query plans |

### Debug Commands

#### Docker

```bash
# Show resource usage
docker stats

# Inspect container
docker inspect <container-id>

# Check network connectivity
docker-compose exec yellowstone-api curl -v redis:6379
```

#### Kubernetes

```bash
# Get detailed pod info
kubectl get pod <pod-name> -n yellowstone -o yaml

# Check pod events
kubectl describe pod <pod-name> -n yellowstone

# View previous pod logs (if crashed)
kubectl logs <pod-name> -n yellowstone --previous

# Check node status
kubectl describe node <node-name>
```

#### Azure

```bash
# Check deployment status
az deployment group show \
  --name yellowstone-deploy \
  --resource-group Yellowstone

# View activity logs
az monitor activity-log list --resource-group Yellowstone

# Check resource health
az resource invoke-action \
  --action healthStatus \
  --resource-group Yellowstone
```

---

## Next Steps

1. **Configure Monitoring**: Update alert email addresses
2. **Set up CI/CD**: Integrate with GitHub Actions
3. **Enable HTTPS**: Configure TLS certificates
4. **Implement Backups**: Set up automated backup policies
5. **Performance Testing**: Run load tests to establish baselines
6. **Security Hardening**: Review and tighten security policies

---

For detailed documentation, see [README.md](./README.md)
