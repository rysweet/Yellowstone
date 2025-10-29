# Yellowstone Deployment Guide

Production-ready deployment infrastructure for Yellowstone Cypher Query Engine across local development, Kubernetes, and Azure Cloud environments.

## Overview

This deployment module provides complete infrastructure-as-code for Yellowstone with:

- **Docker** - Local development and containerization
- **Docker Compose** - Multi-container local environment
- **Kubernetes** - Production orchestration with scalability
- **Azure Bicep** - Cloud infrastructure with private endpoints
- **Security-First** - No public IPs, private endpoints only, RBAC enabled

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Yellowstone Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │   Docker     │  │ Kubernetes   │  │     Azure      │    │
│  │ Development  │  │ (Production) │  │  (Production)  │    │
│  └──────────────┘  └──────────────┘  └────────────────┘    │
│        │                   │                   │             │
│        └───────────────────┴───────────────────┘             │
│                         │                                     │
│                  ┌──────▼─────────┐                          │
│                  │  Application   │                          │
│                  │  & Services    │                          │
│                  └─────────────────┘                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 1. Local Development with Docker

### Quick Start

```bash
cd /home/azureuser/src/Yellowstone

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f yellowstone-api

# Stop services
docker-compose down
```

### Services

| Service | Purpose | Port | Credentials |
|---------|---------|------|-------------|
| yellowstone-api | Main API | 8000 | Auto-configured |
| postgres | Database | 5432 | yellowstone/yellowstone-dev |
| redis | Cache | 6379 | password: yellowstone-dev |
| prometheus | Metrics | 9090 | None required |
| grafana | Dashboards | 3000 | admin/admin |

### Environment Variables

Create `.env` file in deployment directory:

```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
SENTINEL_WORKSPACE_ID=your-workspace-id

# Database
POSTGRES_PASSWORD=secure-password
DATABASE_USER=yellowstone
DATABASE_PASSWORD=secure-password

# Redis
REDIS_PASSWORD=secure-redis-password

# API Keys
CLAUDE_API_KEY=your-claude-api-key

# Grafana
GRAFANA_PASSWORD=secure-grafana-password
```

### Database Initialization

PostgreSQL initializes automatically with:

- Core schemas: `audit`, `metrics`, `queries`
- Audit logging table
- Query history tracking
- Performance metrics collection
- Row-level security policies

Verify initialization:

```bash
docker-compose exec postgres psql -U yellowstone -d yellowstone -c "\dt audit.*"
```

### Monitoring

Access monitoring dashboards:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 2. Kubernetes Deployment

### Prerequisites

```bash
# Azure CLI
az login
az account set --subscription <subscription-id>

# kubectl
kubectl version --client

# Container registry access
az acr login --name <registry-name>
```

### Namespace Setup

```bash
# Create namespace
kubectl create namespace yellowstone

# Label for network policies
kubectl label namespace yellowstone name=yellowstone
kubectl label namespace ingress-nginx name=ingress-nginx
```

### ConfigMaps and Secrets

```bash
# Create configuration
kubectl apply -f kubernetes/configmap.yaml

# Create secrets (use your actual values)
kubectl create secret generic yellowstone-secrets \
  --from-literal=database_user=psqladmin \
  --from-literal=database_password=<secure-password> \
  --from-literal=redis_password=<secure-password> \
  --from-literal=claude_api_key=<api-key> \
  -n yellowstone

# Verify
kubectl get secrets -n yellowstone
```

### Deploy Application

```bash
# Apply deployment and services
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml

# Monitor rollout
kubectl rollout status deployment/yellowstone-api -n yellowstone

# Check pods
kubectl get pods -n yellowstone -o wide
```

### Verify Deployment

```bash
# Port forward to access API
kubectl port-forward -n yellowstone svc/yellowstone-api 8000:8000

# Test API
curl http://localhost:8000/health
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment yellowstone-api --replicas=5 -n yellowstone

# HPA monitors CPU/Memory automatically
kubectl get hpa -n yellowstone

# Watch scaling
kubectl get hpa -n yellowstone --watch
```

### Logs and Monitoring

```bash
# View pod logs
kubectl logs -n yellowstone deployment/yellowstone-api --all-containers=true -f

# Pod debugging
kubectl exec -it -n yellowstone <pod-name> -- /bin/bash

# Resource usage
kubectl top pods -n yellowstone
kubectl top nodes
```

### Security

```bash
# Verify network policies
kubectl get networkpolicies -n yellowstone

# Check RBAC
kubectl get rolebindings -n yellowstone
kubectl get clusterrolebindings | grep yellowstone

# Pod security
kubectl get psp | grep yellowstone
```

## 3. Azure Deployment

### Infrastructure Setup

#### Prerequisites

```bash
# Install Azure CLI and Bicep
az upgrade
az bicep install

# Authenticate
az login
az account set --subscription <subscription-id>

# Verify Yellowstone resource group exists
az group create --name Yellowstone --location eastus
```

#### Deploy Main Infrastructure

```bash
# Validate bicep template
az bicep build --file azure/bicep/main.bicep

# Deploy infrastructure
az deployment group create \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --template-file azure/bicep/main.bicep \
  --parameters environment=prod \
             location=eastus \
             projectName=yellowstone

# Get deployment outputs
az deployment group show \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --query properties.outputs
```

#### Deploy Sentinel Configuration

```bash
# Get Log Analytics workspace ID
WORKSPACE_ID=$(az deployment group show \
  --name yellowstone-deploy \
  --resource-group Yellowstone \
  --query properties.outputs.logAnalyticsId.value -o tsv)

# Deploy Sentinel setup
az deployment group create \
  --name yellowstone-sentinel \
  --resource-group Yellowstone \
  --template-file azure/bicep/sentinel.bicep \
  --parameters logAnalyticsWorkspaceId=$WORKSPACE_ID \
             environment=prod \
             location=eastus
```

### Azure Resources Created

#### Networking

| Resource | Type | Purpose |
|----------|------|---------|
| vnet-yellowstone-prod | VNet | Private network isolation |
| subnet-yellowstone-api | Subnet | Application tier |
| subnet-yellowstone-aks | Subnet | Kubernetes nodes |
| subnet-yellowstone-postgres | Subnet | Database tier |
| nsg-yellowstone-api | NSG | Network access rules |

#### Compute & Storage

| Resource | Type | Purpose |
|----------|------|---------|
| acr-yellowstone | Container Registry | Private image storage |
| psql-yellowstone-prod | PostgreSQL Server | Data persistence |
| redis-yellowstone-prod | Redis Cache | Session/cache layer |

#### Security

| Resource | Type | Purpose |
|----------|------|---------|
| akv-yellowstone-prod | Key Vault | Secrets management |
| pep-keyvault | Private Endpoint | Secure KV access |
| pep-acr | Private Endpoint | Private registry access |
| pep-redis | Private Endpoint | Private cache access |

#### Monitoring

| Resource | Type | Purpose |
|----------|------|---------|
| la-yellowstone-prod | Log Analytics | Logs aggregation |
| appi-yellowstone-prod | App Insights | Application monitoring |
| ag-yellowstone-prod | Action Group | Alert routing |

### Private Endpoints

All services are deployed with private endpoints only - no public IPs:

```bash
# List private endpoints
az network private-endpoint list \
  --resource-group Yellowstone \
  -o table

# View private endpoint connections
az network private-endpoint show \
  --resource-group Yellowstone \
  --name pep-yellowstone-keyvault \
  --query privateLinkServiceConnections
```

### Key Vault Configuration

```bash
# Set administrator policies
az keyvault set-policy \
  --vault-name <kv-name> \
  --object-id <user-object-id> \
  --secret-permissions get list set

# Store secrets
az keyvault secret set \
  --vault-name <kv-name> \
  --name db-password \
  --value <secure-password>

az keyvault secret set \
  --vault-name <kv-name> \
  --name claude-api-key \
  --value <api-key>

# Retrieve secrets
az keyvault secret show \
  --vault-name <kv-name> \
  --name db-password
```

### Azure Container Registry

```bash
# Build and push image
az acr build \
  --registry <acr-name> \
  --image yellowstone:latest \
  --file deployment/Dockerfile \
  .

# List images
az acr repository list --name <acr-name>

# View image tags
az acr repository show-tags \
  --name <acr-name> \
  --repository yellowstone
```

### Monitoring and Alerts

#### View Logs

```bash
# Query audit logs
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "YellowstoneAudit_CL | take 10"

# Performance metrics
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "YellowstoneQueryPerformance_CL | summarize avg(ExecutionTimeMs)"
```

#### Alert Rules

Pre-configured alerts:

- **High Query Response Time**: Triggers when P95 > 5 seconds
- **Query Failure Rate**: Triggers when > 5% queries fail
- **Security Event**: Triggers on critical security events

Configure notification email:

```bash
az monitor action-group create \
  --resource-group Yellowstone \
  --name ag-yellowstone-prod \
  --short-name YS

az monitor action-group update \
  --resource-group Yellowstone \
  --name ag-yellowstone-prod \
  --add-action email-receiver admin \
    --email-address admin@example.com
```

## Environment-Specific Configurations

### Development

```bash
# Local docker-compose
environment: development
log_level: DEBUG
cache_ttl: 300 seconds
rate_limit: 10,000 req/min
trace_sampling: 100%
```

### Staging

```bash
# AKS staging
environment: staging
log_level: INFO
cache_ttl: 1,800 seconds
rate_limit: 5,000 req/min
trace_sampling: 50%
```

### Production

```bash
# Azure production
environment: production
log_level: INFO
cache_ttl: 3,600 seconds
rate_limit: 1,000 req/min
trace_sampling: 10%
```

### Switching Configurations

```bash
# Kubernetes - using dev config
kubectl set env deployment/yellowstone-api \
  --from=configmap=yellowstone-env-dev \
  -n yellowstone

# Switch to staging
kubectl set env deployment/yellowstone-api \
  --from=configmap=yellowstone-env-staging \
  -n yellowstone
```

## Security Best Practices

### Network Security

- Private VNet with no internet-facing endpoints
- Network Security Groups with deny-by-default rules
- Private endpoints for all Azure services
- Network policies in Kubernetes

### Access Control

- Azure RBAC for cloud resources
- Kubernetes RBAC for pod access
- Key Vault for secrets management
- Service accounts with minimal permissions

### Data Protection

- TLS 1.2+ for all connections
- PostgreSQL SSL requirement
- Redis encrypted connections
- Application-level encryption for sensitive fields

### Compliance

- Audit logging enabled
- Comprehensive security event tracking
- Alert rules for suspicious activity
- Retention policies enforced

## Troubleshooting

### Docker Issues

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs <service-name>

# Rebuild and restart
docker-compose up --build --force-recreate
```

### Kubernetes Issues

```bash
# Pod status
kubectl describe pod <pod-name> -n yellowstone

# Check events
kubectl get events -n yellowstone --sort-by='.lastTimestamp'

# Node status
kubectl get nodes
kubectl describe node <node-name>
```

### Azure Issues

```bash
# Check deployment status
az deployment group show \
  --resource-group Yellowstone \
  --name yellowstone-deploy

# View activity log
az monitor activity-log list \
  --resource-group Yellowstone \
  --max-events 50
```

## Maintenance

### Database Backups

```bash
# PostgreSQL automatic backups (14-day retention)
# Managed automatically by Azure

# Manual backup
pg_dump -h <host> -U <user> -d yellowstone > backup.sql
```

### Updates and Patching

```bash
# Update Kubernetes deployment
kubectl set image deployment/yellowstone-api \
  yellowstone-api=<registry>/yellowstone:v1.2 \
  -n yellowstone

# Verify rollout
kubectl rollout status deployment/yellowstone-api -n yellowstone
```

### Cleanup

```bash
# Docker cleanup
docker-compose down -v  # Removes volumes too

# Kubernetes cleanup
kubectl delete deployment yellowstone-api -n yellowstone

# Azure cleanup (destructive)
az group delete --name Yellowstone
```

## Cost Optimization

### Azure Resources

- **PostgreSQL**: Burstable B-series for lower cost, upgrade as needed
- **Redis**: Premium for reliability; Standard for dev/test
- **Container Registry**: Premium for private endpoints; Standard for public

### Kubernetes

- Configure resource requests/limits to optimize node packing
- Use Horizontal Pod Autoscaler for cost-effective scaling
- Spot instances for non-critical workloads

## Support and Documentation

For detailed configuration options and troubleshooting, see:

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Kubernetes Official Docs](https://kubernetes.io/docs/)
- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Microsoft Sentinel Documentation](https://learn.microsoft.com/en-us/azure/sentinel/)
- [Yellowstone Main README](../README.md)

## License

MIT License - See LICENSE file in project root
