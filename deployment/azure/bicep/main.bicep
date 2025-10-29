metadata:
  description: 'Yellowstone Cypher Query Engine - Main Azure Infrastructure'
  version: '1.0.0'

// Parameters
param environment string = 'prod'
param location string = resourceGroup().location
param projectName string = 'yellowstone'
param tags object = {
  environment: environment
  project: projectName
  createdBy: 'terraform'
}

// Naming conventions
var resourceGroupName = resourceGroup().name
var uniqueSuffix = uniqueString(resourceGroup().id)
var acrName = 'acr${projectName}${uniqueSuffix}'
var akvName = 'akv-${projectName}-${environment}'
var postgresServerName = 'psql-${projectName}-${environment}'
var redisCacheName = 'redis-${projectName}-${environment}'
var appInsightsName = 'appi-${projectName}-${environment}'
var actionGroupName = 'ag-${projectName}-${environment}'
var logAnalyticsName = 'la-${projectName}-${environment}'

// VNet and Subnet names
var vnetName = 'vnet-${projectName}-${environment}'
var subnetName = 'subnet-${projectName}-api'
var aksSubnetName = 'subnet-${projectName}-aks'

// Variables
var addressSpace = '10.0.0.0/16'
var apiSubnetPrefix = '10.0.1.0/24'
var aksSubnetPrefix = '10.0.2.0/24'
var postgresSubnetPrefix = '10.0.3.0/24'

// PostgreSQL variables
var postgresSkuName = 'B_Gen5_1'
var postgresVersion = '15'
var postgresBackupRetention = 14
var postgresGeoRedundant = false

// Redis variables
var redisSkuName = 'Premium'
var redisCapacity = 1
var redisVersion = '7'

// Ensure we don't have any public endpoints
var enablePublicNetworkAccess = false

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressSpace
      ]
    }
    subnets: [
      {
        name: apiSubnetName
        properties: {
          addressPrefix: apiSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegation: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.ContainerInstance/containerGroups'
              }
            }
          ]
        }
      }
      {
        name: aksSubnetName
        properties: {
          addressPrefix: aksSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegation: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.ContainerService/managedClusters'
              }
            }
          ]
        }
      }
      {
        name: 'subnet-${projectName}-postgres'
        properties: {
          addressPrefix: postgresSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegation: [
            {
              name: 'Microsoft.DBforPostgreSQL'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

// Network Security Groups
resource apiNsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: 'nsg-${projectName}-api'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'DenyAllInbound'
        properties: {
          description: 'Deny all inbound traffic by default'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Deny'
          priority: 4096
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowVNetInbound'
        properties: {
          description: 'Allow VNet inbound traffic'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'DenyAllOutbound'
        properties: {
          description: 'Deny all outbound traffic by default'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Deny'
          priority: 4096
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowVNetOutbound'
        properties: {
          description: 'Allow VNet outbound traffic'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 100
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowAzureServiceOutbound'
        properties: {
          description: 'Allow outbound to Azure services'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'AzureCloud'
          access: 'Allow'
          priority: 110
          direction: 'Outbound'
        }
      }
    ]
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: akvName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    publicNetworkAccess: 'Disabled'
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
  }
}

// Private Endpoint for Key Vault
resource kvPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pep-${projectName}-keyvault'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: '${vnet.id}/subnets/${apiSubnetName}'
    }
    privateLinkServiceConnections: [
      {
        name: 'keyvault-connection'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: [
            'vault'
          ]
        }
      }
    ]
  }
}

// Private DNS Zone for Key Vault
resource kvPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
  tags: tags
}

// Private DNS Zone VNet Link
resource kvPrivateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: kvPrivateDnsZone
  name: 'vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// DNS Record for Key Vault
resource kvDnsRecord 'Microsoft.Network/privateDnsZones/A@2020-06-01' = {
  parent: kvPrivateDnsZone
  name: akvName
  properties: {
    ttl: 3600
    aRecords: [
      {
        ipv4Address: kvPrivateEndpoint.properties.customDnsConfigs[0].ipAddresses[0]
      }
    ]
  }
}

// Azure Container Registry (Private)
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Premium'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Disabled'
    networkRuleBypassOptions: 'None'
    policies: {
      quarantinePolicy: {
        status: 'enabled'
      }
      retentionPolicy: {
        days: 30
        status: 'enabled'
      }
    }
  }
}

// Private Endpoint for ACR
resource acrPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pep-${projectName}-acr'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: '${vnet.id}/subnets/${apiSubnetName}'
    }
    privateLinkServiceConnections: [
      {
        name: 'acr-connection'
        properties: {
          privateLinkServiceId: acr.id
          groupIds: [
            'registry'
          ]
        }
      }
    ]
  }
}

// PostgreSQL Flexible Server
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresServerName
  location: location
  tags: tags
  sku: {
    name: postgresSkuName
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'psqladmin'
    administratorLoginPassword: 'TempPassword123!@#'  // Override with actual secret
    version: postgresVersion
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: postgresBackupRetention
      geoRedundantBackup: postgresGeoRedundant ? 'Enabled' : 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: '${vnet.id}/subnets/subnet-${projectName}-postgres'
      privateDnsZoneArmResourceId: kvPrivateDnsZone.id
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// PostgreSQL Database
resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgresServer
  name: 'yellowstone'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Redis Cache (Premium with Private Endpoint)
resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisCacheName
  location: location
  tags: tags
  properties: {
    sku: {
      name: redisSkuName
      family: 'P'
      capacity: redisCapacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
    privateEndpointConnections: []
  }
}

// Private Endpoint for Redis
resource redisPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pep-${projectName}-redis'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: '${vnet.id}/subnets/${apiSubnetName}'
    }
    privateLinkServiceConnections: [
      {
        name: 'redis-connection'
        properties: {
          privateLinkServiceId: redisCache.id
          groupIds: [
            'redisCache'
          ]
        }
      }
    ]
  }
}

// Sentinel Workspace (Placeholder - typically created separately)
resource sentinelLogAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'la-${projectName}-sentinel-${environment}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}

// Action Group for Alerts
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'YSAlerts'
    enabled: true
  }
}

// Alert Rule - High Query Response Time
resource queryTimeAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-${projectName}-high-query-time'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when query response time exceeds threshold'
    severity: 2
    enabled: true
    scopes: [
      appInsights.id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      odata.type: 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'Requests/duration'
          metricName: 'performanceCounters/processorCpuTime'
          operator: 'GreaterThan'
          threshold: 5000
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Outputs
output vnetId string = vnet.id
output acrLoginServer string = acr.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output postgresServerName string = postgresServer.name
output redisCacheName string = redisCache.name
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output logAnalyticsId string = logAnalytics.id
output logAnalyticsWorkspaceId string = logAnalytics.properties.customerId
