param location string = resourceGroup().location
param environmentName string = 'dev'
param projectName string = 'apitest'

var uniqueSuffix = uniqueString(resourceGroup().id)
var serviceBusNamespace = '${projectName}-sb-${environmentName}-${uniqueSuffix}'
var functionAppName = '${projectName}-func-${environmentName}-${uniqueSuffix}'
var storageAccountName = '${projectName}st${environmentName}${uniqueSuffix}'
var appInsightsName = '${projectName}-ai-${environmentName}-${uniqueSuffix}'

// Storage Account for Functions
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
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

// Service Bus Namespace and Topic
module serviceBus 'servicebus.bicep' = {
  name: 'serviceBusDeployment'
  params: {
    namespaceName: serviceBusNamespace
    location: location
  }
}

// App Service Plan for Functions
resource hostingPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${functionAppName}-plan'
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true // Linux
  }
}

// FIXED: Get connection string using resource reference
resource serviceBusAuthRule 'Microsoft.ServiceBus/namespaces/authorizationRules@2022-10-01-preview' existing = {
  name: '${serviceBusNamespace}/RootManageSharedAccessKey'
  dependsOn: [serviceBus]
}

// Function App
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
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
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
          value: serviceBusAuthRule.listKeys().primaryConnectionString
        }
        {
          name: 'SLACK_WEBHOOK_URL'
          value: '' // Set this manually after deployment
        }
      ]
    }
  }
}

// FIXED: Don't output secrets, output resource information instead
output functionAppName string = functionApp.name
output resourceGroupName string = resourceGroup().name
output storageAccountName string = storageAccount.name
output appInsightsName string = appInsights.name
output serviceBusNamespace string = serviceBus.outputs.namespaceName
output serviceBusResourceId string = serviceBus.outputs.serviceBusResourceId

// To get the connection string after deployment, use Azure CLI:
// az servicebus namespace authorization-rule keys list --resource-group rg-apitest-dev --namespace-name <namespace> --name RootManageSharedAccessKey --query primaryConnectionString -o tsv
