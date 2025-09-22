param location string = resourceGroup().location
param environmentName string = 'dev'

var uniqueSuffix = uniqueString(resourceGroup().id)
var serviceBusNamespace = 'sb-apitests-${environmentName}-${uniqueSuffix}'
var functionAppName = 'func-apitests-${environmentName}-${uniqueSuffix}'
var storageAccountName = 'stapitests${environmentName}${uniqueSuffix}'
var appInsightsName = 'ai-apitests-${environmentName}-${uniqueSuffix}'

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
  }
}

// Service Bus
module serviceBus 'servicebus.bicep' = {
  name: 'serviceBusDeployment'
  params: {
    namespaceName: serviceBusNamespace
    location: location
  }
}

// Function App
resource hostingPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${functionAppName}-plan'
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.9'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'ServiceBusConnectionString'
          value: serviceBus.outputs.connectionString
        }
        {
          name: 'SLACK_WEBHOOK_URL'
          value: ''  // Set this manually after deployment
        }
      ]
    }
  }
}

output serviceBusConnectionString string = serviceBus.outputs.connectionString
output functionAppName string = functionApp.name
output resourceGroupName string = resourceGroup().name
