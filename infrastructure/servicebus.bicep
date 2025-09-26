param namespaceName string
param location string

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: namespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {}
}

// Create topic for API test results
resource testResultsTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'api-test-results'
  properties: {
    defaultMessageTimeToLive: 'PT1H'
    maxSizeInMegabytes: 1024
  }
}

// Create subscription for Azure Function
resource testResultsSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: testResultsTopic
  name: 'processor'
  properties: {
    defaultMessageTimeToLive: 'PT1H'
    lockDuration: 'PT5M'
    maxDeliveryCount: 10
  }
}

// Authorization rule for connections
resource authRule 'Microsoft.ServiceBus/namespaces/authorizationRules@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'RootManageSharedAccessKey'
  properties: {
    rights: ['Send', 'Listen', 'Manage']
  }
}

// FIXED: Don't output connection string directly, output resource info instead
output namespaceName string = serviceBusNamespace.name
output authRuleName string = authRule.name
output serviceBusResourceId string = serviceBusNamespace.id
