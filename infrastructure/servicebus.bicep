param namespaceName string
param location string

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: namespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
}

resource testResultsTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'api-test-results'
  properties: {
    maxSizeInMegabytes: 1024
  }
}

resource testResultsSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: testResultsTopic
  name: 'processor'
  properties: {
    maxDeliveryCount: 5
  }
}

resource authRule 'Microsoft.ServiceBus/namespaces/authorizationRules@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'RootManageSharedAccessKey'
  properties: {
    rights: ['Send', 'Listen', 'Manage']
  }
}

output connectionString string = listKeys(authRule.id, authRule.apiVersion).primaryConnectionString
