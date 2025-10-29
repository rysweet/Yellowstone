# Yellowstone Deployment Module - File Index

Complete guide to all files in the deployment module.

## Quick Navigation

### Getting Started (Read These First)

1. **Start Here**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
   - Step-by-step instructions for all platforms
   - Prerequisites and verification
   - 608 lines of practical guidance

2. **Understand Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
   - Visual diagrams for all environments
   - Component interactions
   - Data flow and network layout
   - 493 lines with ASCII art diagrams

3. **Reference**: [README.md](./README.md)
   - Comprehensive deployment reference
   - All platform options with examples
   - Security best practices
   - Troubleshooting guide
   - 604 lines of detailed documentation

### Configuration & Setup

4. **Environment Template**: [.env.example](./.env.example)
   - Copy to `.env` before deployment
   - 50+ configuration variables
   - Comments for each section
   - 122 lines

### Deployment Execution

5. **Quick Start Script**: [scripts/deploy.sh](./scripts/deploy.sh)
   - Unified CLI for all platforms
   - Handles Docker, Kubernetes, and Azure
   - 309 lines of production shell script

## File Organization

### Core Infrastructure (9 files)

#### Container & Orchestration

| File | Size | Purpose |
|------|------|---------|
| [Dockerfile](./Dockerfile) | 55 lines | Multi-stage production image |
| [docker-compose.yml](./docker-compose.yml) | 118 lines | 5-service local development stack |
| [prometheus.yml](./prometheus.yml) | 56 lines | Metrics collection configuration |

#### Documentation

| File | Lines | Purpose |
|------|-------|---------|
| [README.md](./README.md) | 604 | Full deployment reference |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | 608 | Step-by-step instructions |
| [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md) | 534 | Module overview |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 493 | Architecture & diagrams |
| [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md) | 400+ | Verification procedures |
| [INDEX.md](./INDEX.md) | This file | Navigation guide |

#### Configuration

| File | Lines | Purpose |
|------|-------|---------|
| [.env.example](./.env.example) | 122 | Environment template |

### Kubernetes (3 files)

| File | Lines | Purpose |
|------|-------|---------|
| [kubernetes/deployment.yaml](./kubernetes/deployment.yaml) | 255 | Deployment + HPA + security |
| [kubernetes/service.yaml](./kubernetes/service.yaml) | 110 | Service + network policies |
| [kubernetes/configmap.yaml](./kubernetes/configmap.yaml) | 221 | ConfigMaps for all environments |

### Azure Bicep (4 files)

| File | Lines | Purpose |
|------|-------|---------|
| [azure/bicep/main.bicep](./azure/bicep/main.bicep) | 497 | Complete infrastructure |
| [azure/bicep/sentinel.bicep](./azure/bicep/sentinel.bicep) | 427 | Sentinel workspace setup |
| [azure/bicep/parameters.dev.json](./azure/bicep/parameters.dev.json) | 23 | Development parameters |
| [azure/bicep/parameters.prod.json](./azure/bicep/parameters.prod.json) | 24 | Production parameters |

### Scripts (2 files)

| File | Lines | Purpose |
|------|-------|---------|
| [scripts/deploy.sh](./scripts/deploy.sh) | 309 | Unified deployment CLI |
| [scripts/init-db.sql](./scripts/init-db.sql) | 228 | PostgreSQL initialization |

### Monitoring (1 file)

| File | Lines | Purpose |
|------|-------|---------|
| [grafana/provisioning/dashboards/yellowstone-main.json](./grafana/provisioning/dashboards/yellowstone-main.json) | 281 | Grafana dashboard |

## By Use Case

### I Want to Deploy Locally (Docker)

Start with: [DEPLOYMENT_GUIDE.md - Local Development](./DEPLOYMENT_GUIDE.md#local-development-with-docker)

Key files:
1. [.env.example](./.env.example) - Copy and configure
2. [docker-compose.yml](./docker-compose.yml) - Run `docker-compose up -d`
3. [scripts/init-db.sql](./scripts/init-db.sql) - Auto-executed by PostgreSQL
4. [Dockerfile](./Dockerfile) - Built automatically

### I Want to Deploy to Kubernetes

Start with: [DEPLOYMENT_GUIDE.md - Kubernetes](./DEPLOYMENT_GUIDE.md#kubernetes-deployment)

Key files:
1. [kubernetes/deployment.yaml](./kubernetes/deployment.yaml) - Main deployment
2. [kubernetes/service.yaml](./kubernetes/service.yaml) - Service + networking
3. [kubernetes/configmap.yaml](./kubernetes/configmap.yaml) - Configuration
4. [scripts/deploy.sh](./scripts/deploy.sh) - Automation

### I Want to Deploy to Azure

Start with: [DEPLOYMENT_GUIDE.md - Azure](./DEPLOYMENT_GUIDE.md#azure-cloud-deployment)

Key files:
1. [azure/bicep/main.bicep](./azure/bicep/main.bicep) - Infrastructure
2. [azure/bicep/sentinel.bicep](./azure/bicep/sentinel.bicep) - Monitoring
3. [azure/bicep/parameters.prod.json](./azure/bicep/parameters.prod.json) - Configuration
4. [scripts/deploy.sh](./scripts/deploy.sh) - Automation

### I Want to Understand the Architecture

Start with: [ARCHITECTURE.md](./ARCHITECTURE.md)

Contains:
- High-level system architecture
- Docker architecture diagram
- Kubernetes cluster layout
- Azure cloud setup
- Network connectivity map
- Data flow diagrams

### I Need to Verify Everything

Start with: [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md)

Covers:
- File structure verification
- Configuration validation
- Security checklist
- Performance settings
- Pre-deployment checklist
- Post-deployment verification

### I Need Complete Reference

Use: [README.md](./README.md)

Includes:
- All platforms with examples
- Service descriptions
- Configuration options
- Security best practices
- Troubleshooting guide
- Cost optimization
- Maintenance procedures

## Technology Stack

### Container & Orchestration

| Component | Version | File |
|-----------|---------|------|
| Docker | Latest | [Dockerfile](./Dockerfile) |
| Docker Compose | 3.8 | [docker-compose.yml](./docker-compose.yml) |
| Kubernetes | 1.24+ | [kubernetes/](./kubernetes/) |

### Data Layer

| Component | Version | File |
|-----------|---------|------|
| PostgreSQL | 16 | [docker-compose.yml](./docker-compose.yml) |
| Redis | 7 | [docker-compose.yml](./docker-compose.yml) |

### Monitoring

| Component | Version | File |
|-----------|---------|------|
| Prometheus | Latest | [prometheus.yml](./prometheus.yml) |
| Grafana | Latest | [grafana/](./grafana/) |
| Log Analytics | - | [azure/bicep/sentinel.bicep](./azure/bicep/sentinel.bicep) |

### Cloud Infrastructure

| Component | Version | File |
|-----------|---------|------|
| Azure Bicep | Latest | [azure/bicep/](./azure/bicep/) |
| Azure CLI | Latest | [scripts/deploy.sh](./scripts/deploy.sh) |

## Configuration Parameters

### Environment Variables (.env)

See [.env.example](./.env.example) with sections:
- Azure credentials (6 vars)
- Database setup (8 vars)
- Redis configuration (4 vars)
- API settings (6 vars)
- Cache options (3 vars)
- Security policies (6 vars)
- Monitoring (4 vars)
- Email/notifications (3 vars)
- Feature flags (2 vars)
- Performance tuning (3 vars)
- Azure Bicep params (6 vars)

### Kubernetes ConfigMap

See [kubernetes/configmap.yaml](./kubernetes/configmap.yaml):
- 20+ base configuration items
- Environment-specific variants (dev/staging/prod)
- Prometheus scrape configuration
- Database initialization SQL

### Azure Parameters

See [azure/bicep/parameters.dev.json](./azure/bicep/parameters.dev.json) and
[azure/bicep/parameters.prod.json](./azure/bicep/parameters.prod.json):
- Environment selection
- Location (Azure region)
- Project naming
- Resource tags

## Database Schema

See [scripts/init-db.sql](./scripts/init-db.sql)

Schemas created:
- `audit` - Compliance logging
- `metrics` - Performance tracking
- `queries` - Query history
- `security` - Security events

Tables (8 total):
- audit.audit_logs
- queries.query_history
- metrics.query_performance
- queries.query_cache
- metrics.alert_rules
- security.security_events
- metrics.api_usage
- queries.query_validation

Views (3 total):
- audit.recent_actions
- metrics.slow_queries
- metrics.error_summary

## Security Components

### Network Security

- VNet segmentation: [azure/bicep/main.bicep](./azure/bicep/main.bicep)
- Network policies: [kubernetes/service.yaml](./kubernetes/service.yaml)
- NSG rules: [azure/bicep/main.bicep](./azure/bicep/main.bicep)

### Access Control

- RBAC configuration: [azure/bicep/main.bicep](./azure/bicep/main.bicep)
- Pod security context: [kubernetes/deployment.yaml](./kubernetes/deployment.yaml)

### Secrets Management

- Key Vault setup: [azure/bicep/main.bicep](./azure/bicep/main.bicep)
- Secret templates: [.env.example](./.env.example)

### Audit & Logging

- Audit tables: [scripts/init-db.sql](./scripts/init-db.sql)
- Log collection: [azure/bicep/sentinel.bicep](./azure/bicep/sentinel.bicep)
- Alerts: [azure/bicep/sentinel.bicep](./azure/bicep/sentinel.bicep)

## Monitoring Setup

### Metrics Collection

- Prometheus config: [prometheus.yml](./prometheus.yml)
- Scraped from: API, PostgreSQL, Redis
- Interval: 15 seconds

### Dashboards

- Main dashboard: [grafana/provisioning/dashboards/yellowstone-main.json](./grafana/provisioning/dashboards/yellowstone-main.json)
- Queries tracked: Response time, QPS, status distribution

### Alerting

- Sentinel alerts: [azure/bicep/sentinel.bicep](./azure/bicep/sentinel.bicep)
- Alert rules (3):
  - High query response time
  - Query failure rate
  - Security threats

## Deployment Procedures

### Using deploy.sh Script

See [scripts/deploy.sh](./scripts/deploy.sh)

Docker commands:
```bash
./scripts/deploy.sh docker up
./scripts/deploy.sh docker down
./scripts/deploy.sh docker build
./scripts/deploy.sh docker logs
./scripts/deploy.sh docker clean
```

Kubernetes commands:
```bash
./scripts/deploy.sh kubernetes create-namespace
./scripts/deploy.sh kubernetes apply-config
./scripts/deploy.sh kubernetes deploy
./scripts/deploy.sh kubernetes status
./scripts/deploy.sh kubernetes logs
./scripts/deploy.sh kubernetes delete
```

Azure commands:
```bash
./scripts/deploy.sh azure validate
./scripts/deploy.sh azure deploy-infra prod Yellowstone
./scripts/deploy.sh azure deploy-sentinel prod Yellowstone
./scripts/deploy.sh azure cleanup
```

### Manual Procedures

See [README.md](./README.md) for detailed manual steps for each platform.

## File Dependencies

```
.env.example
├─ Used by: docker-compose.yml
└─ Used by: deployment scripts

Dockerfile
├─ Used by: docker-compose.yml
└─ Used by: Azure ACR

docker-compose.yml
├─ Uses: Dockerfile
├─ Uses: scripts/init-db.sql
└─ Uses: prometheus.yml

kubernetes/deployment.yaml
├─ References: kubernetes/configmap.yaml
├─ References: kubernetes/service.yaml
└─ Requires: Container image from ACR

kubernetes/configmap.yaml
├─ Embeds: scripts/init-db.sql
├─ Embeds: prometheus.yml
└─ Provides config to: deployment.yaml

azure/bicep/main.bicep
├─ Outputs: Log Analytics workspace ID
└─ Used by: sentinel.bicep

azure/bicep/sentinel.bicep
├─ Requires: Log Analytics workspace ID
└─ Creates monitoring infrastructure

scripts/deploy.sh
├─ Uses: All above files
└─ Orchestrates: Deployment to all platforms

scripts/init-db.sql
├─ Used by: docker-compose.yml (PostgreSQL init)
├─ Embedded in: kubernetes/configmap.yaml
└─ Referenced by: Azure deployment
```

## Documentation Cross-References

- **README.md** - Start here for comprehensive reference
- **DEPLOYMENT_GUIDE.md** - Follow for step-by-step execution
- **ARCHITECTURE.md** - Review for system design understanding
- **VERIFICATION_CHECKLIST.md** - Use to verify successful deployment
- **DEPLOYMENT_SUMMARY.md** - Quick overview of all components
- **INDEX.md** - This file, for navigation

## Version Information

- **Module Version**: 1.0.0
- **Created**: October 29, 2025
- **Status**: Production-Ready
- **Total Files**: 18
- **Total Lines**: 4,965+

## Support & Resources

For detailed information, refer to:

1. **Deployment Help**
   - Docker: See [DEPLOYMENT_GUIDE.md - Docker](./DEPLOYMENT_GUIDE.md#local-development-with-docker)
   - Kubernetes: See [DEPLOYMENT_GUIDE.md - Kubernetes](./DEPLOYMENT_GUIDE.md#kubernetes-deployment)
   - Azure: See [DEPLOYMENT_GUIDE.md - Azure](./DEPLOYMENT_GUIDE.md#azure-cloud-deployment)

2. **Architecture Questions**
   - See [ARCHITECTURE.md](./ARCHITECTURE.md)
   - Includes all diagrams and component layouts

3. **Configuration Issues**
   - See [README.md - Configuration](./README.md#configuration)
   - See [.env.example](./.env.example) with detailed comments

4. **Troubleshooting**
   - See [README.md - Troubleshooting](./README.md#troubleshooting)
   - See [DEPLOYMENT_GUIDE.md - Troubleshooting](./DEPLOYMENT_GUIDE.md#troubleshooting)

5. **Verification**
   - See [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md)
   - Complete pre/post deployment checklist

---

**Next**: Start with [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for your chosen platform.
