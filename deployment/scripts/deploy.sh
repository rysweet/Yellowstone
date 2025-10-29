#!/bin/bash
# Yellowstone Deployment Script
# Handles deployments to Docker, Kubernetes, and Azure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_requirements() {
    local missing=0

    case "$1" in
        docker)
            if ! command -v docker &> /dev/null; then
                log_error "Docker is not installed"
                missing=1
            fi
            if ! command -v docker-compose &> /dev/null; then
                log_error "Docker Compose is not installed"
                missing=1
            fi
            ;;
        kubernetes)
            if ! command -v kubectl &> /dev/null; then
                log_error "kubectl is not installed"
                missing=1
            fi
            if ! command -v helm &> /dev/null; then
                log_warning "Helm is not installed (optional)"
            fi
            ;;
        azure)
            if ! command -v az &> /dev/null; then
                log_error "Azure CLI is not installed"
                missing=1
            fi
            if ! command -v bicep &> /dev/null; then
                log_error "Bicep is not installed"
                missing=1
            fi
            ;;
    esac

    if [ $missing -eq 1 ]; then
        return 1
    fi
    return 0
}

# Docker operations
deploy_docker() {
    local action=$1
    log_info "Docker deployment: $action"

    case "$action" in
        up)
            log_info "Starting Docker services..."
            cd "$DEPLOYMENT_DIR"
            docker-compose up -d
            log_success "Docker services started"
            docker-compose ps
            ;;
        down)
            log_info "Stopping Docker services..."
            cd "$DEPLOYMENT_DIR"
            docker-compose down
            log_success "Docker services stopped"
            ;;
        build)
            log_info "Building Docker image..."
            docker build -f "$DEPLOYMENT_DIR/Dockerfile" \
                -t yellowstone:latest "$PROJECT_DIR"
            log_success "Docker image built"
            ;;
        logs)
            cd "$DEPLOYMENT_DIR"
            docker-compose logs -f yellowstone-api
            ;;
        clean)
            log_info "Cleaning up Docker resources..."
            cd "$DEPLOYMENT_DIR"
            docker-compose down -v
            log_success "Docker cleanup completed"
            ;;
        *)
            log_error "Unknown Docker action: $action"
            return 1
            ;;
    esac
}

# Kubernetes operations
deploy_kubernetes() {
    local action=$1
    local namespace=${2:-yellowstone}

    log_info "Kubernetes deployment: $action (namespace: $namespace)"

    case "$action" in
        create-namespace)
            log_info "Creating Kubernetes namespace..."
            kubectl create namespace "$namespace" || log_warning "Namespace already exists"
            kubectl label namespace "$namespace" name="$namespace" --overwrite
            log_success "Namespace ready"
            ;;
        apply-config)
            log_info "Applying ConfigMaps and Secrets..."
            kubectl apply -f "$DEPLOYMENT_DIR/kubernetes/configmap.yaml"

            # Create secrets if they don't exist
            if ! kubectl get secret yellowstone-secrets -n "$namespace" &> /dev/null; then
                log_warning "yellowstone-secrets not found, creating..."
                kubectl create secret generic yellowstone-secrets \
                    --from-literal=database_user=psqladmin \
                    --from-literal=database_password=change-me \
                    --from-literal=redis_password=change-me \
                    --from-literal=claude_api_key=change-me \
                    -n "$namespace"
            fi
            log_success "Configuration applied"
            ;;
        deploy)
            log_info "Deploying to Kubernetes..."
            kubectl apply -f "$DEPLOYMENT_DIR/kubernetes/deployment.yaml"
            kubectl apply -f "$DEPLOYMENT_DIR/kubernetes/service.yaml"

            log_info "Waiting for rollout..."
            kubectl rollout status deployment/yellowstone-api -n "$namespace"
            log_success "Deployment completed"
            ;;
        status)
            log_info "Deployment status:"
            kubectl get deployment -n "$namespace"
            kubectl get pods -n "$namespace"
            kubectl get svc -n "$namespace"
            ;;
        logs)
            kubectl logs -f deployment/yellowstone-api -n "$namespace"
            ;;
        delete)
            log_warning "Deleting Kubernetes deployment..."
            kubectl delete deployment yellowstone-api -n "$namespace" || true
            kubectl delete svc yellowstone-api -n "$namespace" || true
            log_success "Deployment deleted"
            ;;
        *)
            log_error "Unknown Kubernetes action: $action"
            return 1
            ;;
    esac
}

# Azure deployment
deploy_azure() {
    local action=$1
    local environment=${2:-prod}
    local resource_group=${3:-Yellowstone}

    log_info "Azure deployment: $action (environment: $environment)"

    case "$action" in
        validate)
            log_info "Validating Bicep templates..."
            az bicep build --file "$DEPLOYMENT_DIR/azure/bicep/main.bicep"
            az bicep build --file "$DEPLOYMENT_DIR/azure/bicep/sentinel.bicep"
            log_success "Bicep templates validated"
            ;;
        deploy-infra)
            log_info "Deploying infrastructure to Azure..."
            az deployment group create \
                --name "yellowstone-deploy-$(date +%s)" \
                --resource-group "$resource_group" \
                --template-file "$DEPLOYMENT_DIR/azure/bicep/main.bicep" \
                --parameters "$DEPLOYMENT_DIR/azure/bicep/parameters.${environment}.json"
            log_success "Infrastructure deployed"
            ;;
        deploy-sentinel)
            log_info "Deploying Sentinel configuration..."

            # Get workspace ID
            local workspace_id=$(az deployment group show \
                --name yellowstone-deploy \
                --resource-group "$resource_group" \
                --query properties.outputs.logAnalyticsId.value -o tsv)

            if [ -z "$workspace_id" ]; then
                log_error "Could not retrieve Log Analytics workspace ID"
                return 1
            fi

            az deployment group create \
                --name "yellowstone-sentinel-$(date +%s)" \
                --resource-group "$resource_group" \
                --template-file "$DEPLOYMENT_DIR/azure/bicep/sentinel.bicep" \
                --parameters logAnalyticsWorkspaceId="$workspace_id" \
                            environment="$environment"
            log_success "Sentinel configuration deployed"
            ;;
        cleanup)
            log_warning "Deleting all Azure resources in $resource_group"
            read -p "Are you sure? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                az group delete --name "$resource_group" --yes
                log_success "Resource group deleted"
            fi
            ;;
        *)
            log_error "Unknown Azure action: $action"
            return 1
            ;;
    esac
}

# Main entry point
main() {
    if [ $# -lt 2 ]; then
        cat << EOF
Yellowstone Deployment Script

Usage: $0 <platform> <action> [options]

Platforms:
  docker       Docker Compose operations
  kubernetes   Kubernetes operations
  azure        Azure/Bicep operations

Docker Actions:
  up          Start services
  down        Stop services
  build       Build image
  logs        View logs
  clean       Clean up resources

Kubernetes Actions:
  create-namespace    Create namespace
  apply-config        Apply ConfigMaps/Secrets
  deploy              Deploy application
  status              Show deployment status
  logs                View pod logs
  delete              Delete deployment

Azure Actions:
  validate            Validate Bicep templates
  deploy-infra        Deploy infrastructure
  deploy-sentinel     Deploy Sentinel config
  cleanup             Delete all resources

Examples:
  $0 docker up
  $0 kubernetes create-namespace
  $0 kubernetes deploy yellowstone
  $0 azure validate prod

EOF
        return 1
    fi

    local platform=$1
    local action=$2
    shift 2

    case "$platform" in
        docker)
            check_requirements docker || return 1
            deploy_docker "$action"
            ;;
        kubernetes)
            check_requirements kubernetes || return 1
            deploy_kubernetes "$action" "$@"
            ;;
        azure)
            check_requirements azure || return 1
            deploy_azure "$action" "$@"
            ;;
        *)
            log_error "Unknown platform: $platform"
            return 1
            ;;
    esac
}

main "$@"
