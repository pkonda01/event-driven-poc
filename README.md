# Simple API Testing POC

Event-driven API testing that triggers automatically on code commits using GitHub Actions, Minikube, Azure Functions, and Service Bus.

## 🎯 Use Case

Developer commits API tests → GitHub Actions triggers → Tests run in Minikube → Results sent to Azure Service Bus → Azure Function processes results → Slack notification sent

## 🚀 Quick Start

### 1. Setup
```bash
./scripts/setup.sh
```

### 2. Configure GitHub Secrets
Add these secrets to your GitHub repository:
- `SERVICE_BUS_CONNECTION_STRING` - From Azure Service Bus
- `FUNCTION_APP_NAME` - From Azure deployment  
- `AZURE_CREDENTIALS` - Service principal JSON
- `SLACK_WEBHOOK_URL` - Slack incoming webhook (optional)

### 3. Configure API Tests
Edit `tests/test_config.json` to add your API endpoints:
```json
{
  "api_tests": [
    {
      "name": "My API Health Check",
      "url": "https://myapi.com/health",
      "method": "GET",
      "expected_status": 200,
      "timeout": 10
    }
  ]
}
```

### 4. Commit and Push
Any commit to `main` or `develop` branches will trigger the API tests!

## 🏗️ Architecture

```
Code Commit → GitHub Actions → API Tests → Azure Service Bus → Azure Function → Slack
```

## 📁 Project Structure

- `tests/` - API test definitions and runner
- `infrastructure/` - Azure Bicep templates  
- `functions/` - Azure Function for result processing
- `k8s/` - Kubernetes manifests for Minikube
- `.github/workflows/` - GitHub Actions workflow

## 🧪 Running Tests Locally

```bash
cd tests
export SERVICE_BUS_CONNECTION_STRING="your-connection-string"
python api_tests.py
```

## 📊 Test Results

Results are automatically:
- ✅ Sent to Azure Service Bus
- 🔄 Processed by Azure Function  
- 📢 Posted to Slack (if configured)
- 📋 Available in GitHub Actions logs

## 🔧 Customization

### Adding New Tests
Edit `tests/test_config.json` and add your test configuration.

### Custom Notifications
Update the Azure Function in `functions/TestResultProcessor/__init__.py` to send notifications to your preferred system.

### Different Test Types
Extend `tests/api_tests.py` to support additional test types or validation rules.

## 🎓 What You'll Learn

- ✅ Event-driven testing architecture
- ✅ GitHub Actions automation  
- ✅ Azure Service Bus messaging
- ✅ Azure Functions serverless computing
- ✅ Kubernetes job execution
- ✅ Infrastructure as Code with Bicep

Perfect for learning modern DevOps and cloud-native testing patterns!