#!/bin/bash

# Azure Sentinel Integration Tests Runner
# This script helps run integration tests safely with proper setup checks

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Azure Sentinel Integration Tests Runner"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Please create .env from template:"
    echo "  cp .env.template .env"
    echo "  nano .env  # Edit with your Azure configuration"
    exit 1
fi

# Load environment variables
echo "Loading environment from .env..."
set -a
source .env
set +a

# Check required variables
REQUIRED_VARS=(
    "AZURE_SUBSCRIPTION_ID"
    "AZURE_RESOURCE_GROUP"
    "AZURE_LOCATION"
)

missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}ERROR: Required environment variables not set:${NC}"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please edit .env and set these variables"
    exit 1
fi

# Check if integration tests are enabled
if [ "$RUN_INTEGRATION_TESTS" != "true" ]; then
    echo -e "${YELLOW}WARNING: Integration tests are disabled${NC}"
    echo ""
    echo "These tests create real Azure resources and incur costs."
    echo "To enable, set in .env:"
    echo "  RUN_INTEGRATION_TESTS=\"true\""
    echo ""
    read -p "Do you want to enable and continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
    export RUN_INTEGRATION_TESTS="true"
fi

# Check Azure CLI authentication
echo ""
echo "Checking Azure CLI authentication..."
if ! az account show &> /dev/null; then
    echo -e "${RED}ERROR: Not logged in to Azure CLI${NC}"
    echo "Please login:"
    echo "  az login"
    exit 1
fi

# Get current subscription
current_sub=$(az account show --query id -o tsv)
if [ "$current_sub" != "$AZURE_SUBSCRIPTION_ID" ]; then
    echo -e "${YELLOW}WARNING: Current subscription doesn't match configuration${NC}"
    echo "Current: $current_sub"
    echo "Expected: $AZURE_SUBSCRIPTION_ID"
    echo ""
    read -p "Switch to configured subscription? (yes/no): " switch_sub
    if [ "$switch_sub" == "yes" ]; then
        az account set --subscription "$AZURE_SUBSCRIPTION_ID"
        echo "Subscription switched"
    fi
fi

# Display configuration
echo ""
echo "Configuration:"
echo "  Subscription: $AZURE_SUBSCRIPTION_ID"
echo "  Resource Group: $AZURE_RESOURCE_GROUP"
echo "  Location: $AZURE_LOCATION"
echo "  Workspace: ${AZURE_WORKSPACE_NAME:-auto-generated}"
echo ""

# Cost warning
echo -e "${YELLOW}=========================================="
echo "COST WARNING"
echo "==========================================${NC}"
echo "These tests will create real Azure resources:"
echo "  - Log Analytics Workspace"
echo "  - Azure Sentinel (enabled on workspace)"
echo "  - Custom tables with test data"
echo ""
echo "Estimated cost per run: \$0.10 - \$1.00"
echo "Resources will be deleted after tests complete."
echo ""

# Final confirmation
read -p "Proceed with integration tests? (yes/no): " final_confirm
if [ "$final_confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
if ! python3 -c "import azure.identity" &> /dev/null; then
    echo -e "${YELLOW}WARNING: Azure SDK packages not installed${NC}"
    read -p "Install dependencies from requirements.txt? (yes/no): " install_deps
    if [ "$install_deps" == "yes" ]; then
        pip install -r ../../requirements.txt
    else
        echo "Please install dependencies manually:"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
fi

# Run tests
echo ""
echo -e "${GREEN}Starting integration tests...${NC}"
echo ""

# Determine pytest options
PYTEST_ARGS="-v"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            PYTEST_ARGS="$PYTEST_ARGS -s --log-cli-level=DEBUG"
            shift
            ;;
        --fast)
            PYTEST_ARGS="$PYTEST_ARGS -m 'integration and not slow'"
            shift
            ;;
        --test=*)
            TEST_NAME="${1#*=}"
            PYTEST_ARGS="$PYTEST_ARGS -k $TEST_NAME"
            shift
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Run pytest
cd ../..  # Go to project root
pytest tests/sentinel_integration/ $PYTEST_ARGS

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "Integration tests completed successfully"
    echo "==========================================${NC}"
else
    echo -e "${RED}=========================================="
    echo "Integration tests failed"
    echo "==========================================${NC}"
    echo "Check logs above for details"
fi

echo ""
echo "Remember to check your Azure billing dashboard!"

exit $exit_code
