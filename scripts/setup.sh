#!/bin/bash
set -e

echo "🚀 Setting up API Testing POC"

# Check prerequisites
echo "🔍 Checking prerequisites..."
missing_tools=()

if ! command -v az &> /dev/null; then
    missing_tools+=("Azure CLI")
fi

if ! command -v kubectl &> /dev/null; then
    missing_tools+=("kubectl")
fi

if ! command -v minikube &> /dev/null; then
    missing_tools+=("Minikube")
fi

if ! command -v python3 &> /dev/null; then
    missing_tools+=("Python 3")
fi

if [ ${#missing_tools[@]} -ne 0 ]; then
    echo "❌ Missing required tools:"
    printf '%s\n' "${missing_tools[@]}"
    exit 1
fi

echo "✅ All prerequisites are installed"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r tests/requirements.txt

# Setup Azure (optional)
echo ""
read -p "Setup Azure infrastructure? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔐 Logging into Azure..."
    az login
    
    echo "🏗️ Creating resource group..."
    az group create --name rg-api-tests-dev --location eastus2
    
    echo "🚀 Deploying infrastructure..."
    OUTPUT=$(az deployment group create \
        --resource-group rg-api-tests-dev \
        --template-file infrastructure/main.bicep \
        --parameters environmentName=dev \
        --query 'properties.outputs' \
        --output json)
    
    SERVICE_BUS_CONNECTION=$(echo $OUTPUT | jq -r '.serviceBusConnectionString.value')
    FUNCTION_APP_NAME=$(echo $OUTPUT | jq -r '.functionAppName.value')
    
    echo "✅ Azure infrastructure deployed!"
    echo ""
    echo "📋 Configuration:"
    echo "   Function App: $FUNCTION_APP_NAME"
    echo "   Resource Group: rg-api-tests-dev"
    echo ""
    echo "🔐 Add these secrets to your GitHub repository:"
    echo "   SERVICE_BUS_CONNECTION_STRING: (copy from Azure portal)"
    echo "   FUNCTION_APP_NAME: $FUNCTION_APP_NAME"
    echo "   AZURE_CREDENTIALS: (service principal JSON)"
fi

# Setup Minikube (optional)
echo ""
read -p "Setup Minikube for local testing? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Starting Minikube..."
    minikube start --memory=2048 --cpus=2
    
    echo "✅ Minikube is ready!"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🚀 Next steps:"
echo "   1. Configure GitHub secrets (see above)"
echo "   2. Update test_config.json with your API endpoints"
echo "   3. Commit code to trigger the workflow"
echo ""
echo "🧪 To run tests locally:"
echo "   cd tests && python api_tests.py"