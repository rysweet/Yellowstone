# Yellowstone Deployment Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Yellowstone Cypher Query Engine                      │
│                        Multi-Environment Setup                           │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌───────────────────────────┐
                    │   Development (Docker)    │
                    │  Local Single Machine     │
                    └───────────┬───────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼─────┐ ┌──────▼────┐ ┌───────▼────┐
        │Yellowstone  │ │PostgreSQL │ │   Redis    │
        │    API      │ │  Database │ │   Cache    │
        └─────────────┘ └───────────┘ └────────────┘

                    ┌───────────────────────────┐
                    │  Staging (Kubernetes)     │
                    │   Multi-Node Cluster      │
                    └───────────┬───────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
    ┌───▼────┐  ┌────────────┐ │ ┌──────────────────┐ │
    │ Master │  │  Worker 1  │ │ │   Worker 2       │ │
    │  Node  │  ├─────────────┤ │ ├──────────────────┤ │
    └────────┘  │ Pod Replica │ │ │ Pod Replica      │ │
                │  (replica 1)│ │ │ (replica 2)      │ │
                └─────────────┘ │ └──────────────────┘ │
                                │                       │
                    ┌───────────▼─────────────┐
                    │  Shared Storage Layer   │
                    │  PostgreSQL | Redis     │
                    └───────────────────────┘

                    ┌───────────────────────────┐
                    │  Production (Azure)       │
                    │   Fully Managed Cloud     │
                    └───────────┬───────────────┘
                                │
┌───────────────────────────────┼───────────────────────────────┐
│                              VNet                             │
│               (10.0.0.0/16 - Private Network)                 │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            API Tier (10.0.1.0/24)                   │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  Container Instances / AKS Nodes           │   │   │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐               │   │   │
│  │  │  │ Pod1 │ │ Pod2 │ │ Pod3 │               │   │   │
│  │  │  └──────┘ └──────┘ └──────┘               │   │   │
│  │  │  Yellowstone API Replicas (HPA 3-10)     │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────┼────────────────────────┐        │
│  │                        │                        │        │
│  ▼                        ▼                        ▼        │
│ ┌────────────────┐  ┌─────────────┐  ┌──────────────────┐ │
│ │   PostgreSQL   │  │ Redis Cache │  │    Key Vault     │ │
│ │ Flexible Server│  │   (Premium) │  │   (Private EP)   │ │
│ │ (10.0.3.0/24)  │  │(10.0.1.0/24)│  │                  │ │
│ └────────────────┘  └─────────────┘  └──────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Container Registry (ACR) - Private                  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ yellowstone:latest                             │  │   │
│  │  │ yellowstone:v1.0                               │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│              Monitoring & Logging (Out of VNet)               │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  Log Analytics   │  │  Application     │                 │
│  │   Workspace      │  │  Insights        │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                               │
│         ┌─────────────────────────┐                          │
│         │  Sentinel Workspace     │                          │
│         │  - Custom Log Tables    │                          │
│         │  - Alert Rules          │                          │
│         │  - Saved Searches       │                          │
│         └─────────────────────────┘                          │
└───────────────────────────────────────────────────────────────┘
```

## Docker Development Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Setup                      │
│                  Single Host Development                     │
└─────────────────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────┐
        │      Docker Network: yellowstone-network │
        │                                          │
        │  ┌──────────────────────────────────┐   │
        │  │  yellowstone-api:8000           │   │
        │  │  ├─ HTTP: 0.0.0.0:8000         │   │
        │  │  ├─ Metrics: :9090              │   │
        │  │  └─ Health: /health             │   │
        │  └──────────────────────────────────┘   │
        │              │                          │
        │  ┌───────────┼───────────┐              │
        │  │           │           │              │
        │  ▼           ▼           ▼              │
        │ ┌─────┐  ┌─────────┐  ┌───────┐        │
        │ │ PG  │  │ Redis   │  │Prom   │        │
        │ │5432 │  │ 6379    │  │9090   │        │
        │ └─────┘  └─────────┘  └───────┘        │
        │            │                           │
        │  ┌─────────┴─────────┐                 │
        │  ▼                   ▼                  │
        │ ┌──────────────┐ ┌──────────────┐     │
        │ │  Grafana     │ │  Volumes     │     │
        │ │  3000        │ │  - pg-data   │     │
        │ └──────────────┘ │  - redis-data│     │
        │                  │  - prom-data │     │
        │                  │  - logs      │     │
        │                  └──────────────┘     │
        └──────────────────────────────────────────┘

Service Addresses (internal to network):
- API:         yellowstone-api:8000
- Database:    postgres:5432
- Cache:       redis:6379
- Metrics:     prometheus:9090
- Dashboard:   grafana:3000
```

## Kubernetes Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            Kubernetes Cluster Architecture                   │
│                      namespace: yellowstone                  │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────┐
    │           Service Layer (ClusterIP)              │
    │        yellowstone-api:8000/9090                │
    └─────────────────┬────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    ┌────▼──┐    ┌────▼──┐   ┌────▼──┐
    │Pod 1  │    │Pod 2  │   │Pod 3  │
    │(Ready)│    │(Ready)│   │(Ready)│
    └───┬───┘    └───┬───┘   └───┬───┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────┴────────────┐
        │  HPA (3-10 replicas)    │
        │  - CPU: 70%             │
        │  - Memory: 80%          │
        └─────────────────────────┘

    ConfigMap: yellowstone-config
    ├─ environment: production
    ├─ log_level: INFO
    ├─ cache_ttl_seconds: 3600
    └─ ... (20+ settings)

    Secret: yellowstone-secrets
    ├─ database_user
    ├─ database_password
    ├─ redis_password
    └─ claude_api_key

    Network Policies:
    ├─ Ingress: Allow from ingress-nginx namespace
    ├─ Egress: Allow to VNet, DNS, Azure services
    └─ Default: Deny all

    Pod Disruption Budget:
    └─ minAvailable: 2 (always 2+ pods running)

    Pod Anti-Affinity:
    └─ Spread pods across nodes when possible
```

## Azure Cloud Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Azure Cloud (Yellowstone RG)                 │
│                     Production Environment                        │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                Virtual Network (10.0.0.0/16)                    │
│                   Private Network Isolation                      │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │             API Tier Subnet (10.0.1.0/24)                │  │
│ │                                                           │  │
│ │  ┌─────────────────────────────────────────────────┐    │  │
│ │  │   Azure Container Instances / AKS Node         │    │  │
│ │  │   ┌────────────────────────────────────────┐  │    │  │
│ │  │   │    Yellowstone API Deployment          │  │    │  │
│ │  │   │    ├─ Replicas: 3-10 (HPA)             │  │    │  │
│ │  │   │    ├─ Security Context: Non-root       │  │    │  │
│ │  │   │    ├─ Resource Limits:                 │  │    │  │
│ │  │   │    │  CPU: 250m-500m                   │  │    │  │
│ │  │   │    │  Memory: 512Mi-1Gi                │  │    │  │
│ │  │   │    └─ Probes: Liveness, Readiness     │  │    │  │
│ │  │   └────────────────────────────────────────┘  │    │  │
│ │  │                                              │    │  │
│ │  │   Pull Image From:                          │    │  │
│ │  │   └─ ACR (Private Endpoint)                 │    │  │
│ │  └─────────────────────────────────────────────────┘    │  │
│ │                                                           │  │
│ │  NSG Rules (Deny by Default):                           │  │
│ │  ├─ Allow: VNet ingress                                │  │
│ │  ├─ Allow: VNet egress to DB/Cache                     │  │
│ │  ├─ Allow: Egress to AzureCloud (443)                  │  │
│ │  └─ Deny: All others                                   │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │          Database Tier Subnet (10.0.3.0/24)              │  │
│ │                                                           │  │
│ │  ┌──────────────────────────────────┐                   │  │
│ │  │ PostgreSQL Flexible Server (15)  │                   │  │
│ │  │ ├─ Tier: Burstable (B_Gen5_1)   │                   │  │
│ │  │ ├─ Storage: 32GB                 │                   │  │
│ │  │ ├─ Backup: 14 days retention     │                   │  │
│ │  │ ├─ Replication: Zone Redundant   │                   │  │
│ │  │ ├─ SSL: Required (TLS 1.2+)      │                   │  │
│ │  │ └─ Network: Private only         │                   │  │
│ │  └──────────────────────────────────┘                   │  │
│ │  Database:                                              │  │
│ │  ├─ Schemas: audit, metrics, queries, security         │  │
│ │  ├─ Tables: 19 with 50+ indices                        │  │
│ │  └─ Initialization: Automated via init-db.sql          │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │           Cache Tier (API Subnet)                        │  │
│ │                                                           │  │
│ │  ┌──────────────────────────────────┐                   │  │
│ │  │  Redis Premium (1 GB)            │                   │  │
│ │  │  ├─ Cluster: Not required        │                   │  │
│ │  │  ├─ Port: 6379 (private)         │                   │  │
│ │  │  ├─ SSL: Enabled (TLS 1.2+)      │                   │  │
│ │  │  └─ Network: Private Endpoint    │                   │  │
│ │  └──────────────────────────────────┘                   │  │
│ └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Container Registry (Private)                  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Azure Container Registry (Premium)                     │  │
│  │  ├─ Registry: acryellowstone<hash>.azurecr.io          │  │
│  │  ├─ Network: Private Endpoint                          │  │
│  │  ├─ Access: RBAC only (no public IPs)                  │  │
│  │  └─ Images:                                            │  │
│  │     ├─ yellowstone:latest                             │  │
│  │     └─ yellowstone:v1.0                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Security & Key Management                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Azure Key Vault (Standard)                             │  │
│  │  ├─ Network: Private Endpoint (in VNet)               │  │
│  │  ├─ Authorization: RBAC only                           │  │
│  │  ├─ Purge Protection: Enabled                          │  │
│  │  ├─ Soft Delete: 90 days                               │  │
│  │  └─ Secrets:                                           │  │
│  │     ├─ database-password                              │  │
│  │     ├─ claude-api-key                                 │  │
│  │     ├─ redis-password                                 │  │
│  │     └─ ... (managed by operators)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 Monitoring & Observability                      │
│                   (Outside VNet)                                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Log Analytics Workspace                               │  │
│  │  ├─ Custom Tables:                                     │  │
│  │  │  ├─ YellowstoneAudit_CL                            │  │
│  │  │  ├─ YellowstoneQueryPerformance_CL                 │  │
│  │  │  └─ YellowstoneSecurityEvents_CL                   │  │
│  │  ├─ Retention: 30 days default, 90 for Sentinel      │  │
│  │  ├─ Queries: KQL for analysis                        │  │
│  │  └─ Network: Private ingestion (with PE)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Application Insights                                  │  │
│  │  ├─ Instrumentation Key: From deployment outputs     │  │
│  │  ├─ Workspace: Connected to Log Analytics            │  │
│  │  └─ Tracks: Requests, dependencies, exceptions       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Sentinel Workspace                                   │  │
│  │  ├─ Alert Rules:                                     │  │
│  │  │  ├─ High query response time (>5s)               │  │
│  │  │  ├─ Query failure rate (>5%)                     │  │
│  │  │  └─ Security threats (real-time)                │  │
│  │  ├─ Saved Searches:                                 │  │
│  │  │  ├─ Critical errors                             │  │
│  │  │  ├─ Slow queries                                │  │
│  │  │  └─ Security events                             │  │
│  │  └─ Data Collection Rules:                         │  │
│  │     └─ Syslog, Windows events, custom logs         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Action Group                                          │  │
│  │  ├─ Alert Recipients: Email addresses                 │  │
│  │  └─ Connected to: Alert rules in Sentinel            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        User / Client                              │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ Cypher Query (HTTP POST)
                 ▼
         ┌───────────────────┐
         │  Load Balancer /  │
         │  API Gateway      │
         └────────┬──────────┘
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│ Pod 1  │  │ Pod 2  │  │ Pod 3  │
└────┬───┘  └────┬───┘  └────┬───┘
     │           │           │
     │ Check Cache (Redis)   │
     │◄──────────┼───────────┤
     │           │           │
     │ (miss) ▼  ▼  ▼        │
     │    ┌──────────────┐   │
     │    │  Query       │   │
     │    │  Translator  │   │
     │    └──────┬───────┘   │
     │           │           │
     │           ▼ (cache) ▼ │
     │    ┌──────────────┐   │
     │    │  Redis Cache │   │
     │    └──────┬───────┘   │
     │           │ (hit)     │
     │           ▼           │
     │    ┌──────────────┐   │
     │    │ PostgreSQL   │   │
     │    │ Query Log &  │   │
     │    │ Metadata     │   │
     │    └──────────────┘   │
     │                       │
     └────────────┬──────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Format Result  │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Log Audit Event │◄──┐
         └────────┬────────┘   │
                  │            │ PostgreSQL
                  ▼            │ audit.audit_logs
         ┌─────────────────┐   │
         │ Return Response │───┘
         │  (JSON)         │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ User / Client   │
         └─────────────────┘
```

## Component Interactions

```
Application Layer:
┌─────────────────────────────────────────────────────────┐
│             Yellowstone API (Python)                    │
│                                                         │
│  ├─ Query Parser (ANTLR)                              │
│  ├─ Query Optimizer                                   │
│  ├─ Translator (KQL/AI)                               │
│  ├─ Authorization & Security                          │
│  └─ Audit Logger                                      │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌──────┐    ┌─────────┐  ┌──────────┐
    │Redis │    │Postgres │  │  Azure   │
    │Cache │    │Database │  │Services  │
    │(Hot) │    │(Warm)   │  │(External)│
    └──────┘    └─────────┘  └──────────┘
        │            │            │
        └────┬───────┴────────────┘
             │
        ┌────▼───────────┐
        │ Metrics &      │
        │ Observability  │
        │ Stack          │
        └────────────────┘
```

## Deployment Pipeline

```
┌────────────────────────────────────────────────────────────┐
│                   Source Code (Git)                        │
└─────────────────────┬──────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼──┐  ┌──────▼────┐  ┌─────▼─────┐
   │ Docker │  │Kubernetes │  │   Azure   │
   │  Build │  │  Manifest │  │   Bicep   │
   └────┬──┘  └──────┬─────┘  └─────┬─────┘
        │            │             │
        ▼            ▼             ▼
   ┌────────────────────────────────────────────┐
   │  Deployment Targets (environment-specific) │
   │                                            │
   │  ├─ Development (Docker)                 │
   │  ├─ Staging (Kubernetes)                 │
   │  └─ Production (Azure)                   │
   └────────────────────────────────────────────┘
```

## Network Connectivity Map

```
┌──────────────────────────────────────────────────────────────┐
│              Network Connectivity Flow                       │
└──────────────────────────────────────────────────────────────┘

VNet Private Network:
- API Pods ←→ PostgreSQL (port 5432)
- API Pods ←→ Redis (port 6379)
- API Pods ←→ Key Vault (via PE)
- API Pods ←→ Container Registry (via PE)

External Connectivity (Outbound Only):
- API Pods → Azure Services (443 via PE)
- API Pods → DNS (53 UDP)
- API Pods → Claude API (443, via NAT Gateway if needed)

No Inbound from Internet:
- No public IPs on any resource
- No NSG rules allowing internet access
- All ingress through private endpoints
- All egress restricted by NSG rules
```

---

This architecture ensures:

1. **Security**: Private-only, no public IPs, network segmentation
2. **Scalability**: HPA-managed replicas, multi-node Kubernetes
3. **Reliability**: Multi-replica setup, PDB, health checks
4. **Observability**: Comprehensive logging, metrics, alerting
5. **Manageability**: Unified deployment scripts, environment configs
