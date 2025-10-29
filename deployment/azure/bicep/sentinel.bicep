metadata:
  description: 'Yellowstone - Microsoft Sentinel Workspace Setup'
  version: '1.0.0'

// Parameters
param environment string = 'prod'
param location string = resourceGroup().location
param projectName string = 'yellowstone'
param logAnalyticsWorkspaceId string
param retentionInDays int = 90
param tags object = {
  environment: environment
  project: projectName
  createdBy: 'bicep'
}

// Variables
var sentinelWorkspaceName = 'sentinel-${projectName}-${environment}'
var dataCollectionRuleName = 'dcr-${projectName}-logs'
var diagnosticSettingName = 'diag-${projectName}-sentinel'

// Data Collection Rule for Yellowstone logs
resource dataCollectionRule 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: dataCollectionRuleName
  location: location
  tags: tags
  properties: {
    description: 'Collects Yellowstone application logs'
    dataFlows: [
      {
        streams: [
          'Microsoft-Syslog'
          'Microsoft-Event'
        ]
        destinations: [
          'LogAnalyticsWorkspace'
        ]
      }
    ]
    dataSources: {
      syslog: [
        {
          streams: [
            'Microsoft-Syslog'
          ]
          facilityNames: [
            'auth'
            'authpriv'
            'cron'
            'daemon'
            'mark'
            'news'
            'syslog'
            'user'
            'uucp'
            'local0'
            'local1'
            'local2'
            'local3'
            'local4'
            'local5'
            'local6'
            'local7'
          ]
          logLevels: [
            'Debug'
            'Info'
            'Notice'
            'Warning'
            'Error'
            'Critical'
            'Alert'
            'Emergency'
          ]
          name: 'syslog-all'
        }
      ]
      windowsEventLogs: [
        {
          streams: [
            'Microsoft-Event'
          ]
          xPathQueries: [
            'Application!*[System[(Level=1 or Level=2 or Level=3)]]'
            'System!*[System[(Level=1 or Level=2 or Level=3)]]'
            'Security!*[System[(Level=1 or Level=2 or Level=3)]]'
          ]
          name: 'eventLogsAll'
        }
      ]
    }
    destinations: {
      logAnalytics: [
        {
          workspaceResourceId: logAnalyticsWorkspaceId
          name: 'LogAnalyticsWorkspace'
        }
      ]
    }
  }
}

// Custom Log Tables for Yellowstone
resource auditLogsTable 'Microsoft.OperationalInsights/workspaces/tables@2023-09-01' = {
  name: '${split(logAnalyticsWorkspaceId, '/')[8]}/YellowstoneAudit_CL'
  properties: {
    schema: {
      name: 'YellowstoneAudit_CL'
      columns: [
        {
          name: 'TimeGenerated'
          type: 'datetime'
          isDefaultTable: false
        }
        {
          name: 'UserId'
          type: 'string'
        }
        {
          name: 'Action'
          type: 'string'
        }
        {
          name: 'ResourceType'
          type: 'string'
        }
        {
          name: 'ResourceId'
          type: 'string'
        }
        {
          name: 'Details'
          type: 'dynamic'
        }
        {
          name: 'SourceIp'
          type: 'string'
        }
        {
          name: 'Status'
          type: 'string'
        }
        {
          name: 'ErrorMessage'
          type: 'string'
        }
      ]
    }
  }
}

// Query Performance Logs Table
resource queryPerformanceTable 'Microsoft.OperationalInsights/workspaces/tables@2023-09-01' = {
  name: '${split(logAnalyticsWorkspaceId, '/')[8]}/YellowstoneQueryPerformance_CL'
  properties: {
    schema: {
      name: 'YellowstoneQueryPerformance_CL'
      columns: [
        {
          name: 'TimeGenerated'
          type: 'datetime'
        }
        {
          name: 'QueryId'
          type: 'string'
        }
        {
          name: 'QueryHash'
          type: 'string'
        }
        {
          name: 'ExecutionTimeMs'
          type: 'int'
        }
        {
          name: 'MemoryUsedMb'
          type: 'real'
        }
        {
          name: 'CpuUsagePercent'
          type: 'real'
        }
        {
          name: 'ResultCount'
          type: 'int'
        }
        {
          name: 'Status'
          type: 'string'
        }
        {
          name: 'CypherQuery'
          type: 'string'
        }
        {
          name: 'KqlQuery'
          type: 'string'
        }
      ]
    }
  }
}

// Security Events Table
resource securityEventsTable 'Microsoft.OperationalInsights/workspaces/tables@2023-09-01' = {
  name: '${split(logAnalyticsWorkspaceId, '/')[8]}/YellowstoneSecurityEvents_CL'
  properties: {
    schema: {
      name: 'YellowstoneSecurityEvents_CL'
      columns: [
        {
          name: 'TimeGenerated'
          type: 'datetime'
        }
        {
          name: 'EventType'
          type: 'string'
        }
        {
          name: 'Severity'
          type: 'string'
        }
        {
          name: 'UserId'
          type: 'string'
        }
        {
          name: 'IpAddress'
          type: 'string'
        }
        {
          name: 'Description'
          type: 'string'
        }
        {
          name: 'ThreatLevel'
          type: 'string'
        }
        {
          name: 'RemediationAction'
          type: 'string'
        }
      ]
    }
  }
}

// Saved Search - Critical Errors
resource criticalErrorsSearch 'Microsoft.OperationalInsights/workspaces/savedSearches@2023-09-01' = {
  name: '${split(logAnalyticsWorkspaceId, '/')[8]}/critical-errors'
  properties: {
    displayName: 'Yellowstone - Critical Errors'
    category: 'Yellowstone'
    query: '''
YellowstoneAudit_CL
| where Status == "Error"
| where severity >= "Critical"
| summarize Count = count() by Action, ResourceType
| sort by Count desc
    '''
    version: 2
  }
}

// Saved Search - Query Performance
resource queryPerformanceSearch 'Microsoft.OperationalInsights/workspaces/savedSearches@2023-09-01' = {
  name: '${split(logAnalyticsWorkspaceId, '/')[8]}/query-performance'
  properties: {
    displayName: 'Yellowstone - Query Performance Analysis'
    category: 'Yellowstone'
    query: '''
YellowstoneQueryPerformance_CL
| summarize
    AvgTimeMs = avg(ExecutionTimeMs),
    MaxTimeMs = max(ExecutionTimeMs),
    MinTimeMs = min(ExecutionTimeMs),
    P95TimeMs = percentile(ExecutionTimeMs, 95),
    Count = count()
  by QueryHash
| where AvgTimeMs > 1000
| sort by AvgTimeMs desc
    '''
    version: 2
  }
}

// Saved Search - Security Events
resource securityEventsSearch 'Microsoft.OperationalInsights/workspaces/savedSearches@2023-09-01' = {
  name: '${split(logAnalyticsWorkspaceId, '/')[8]}/security-events'
  properties: {
    displayName: 'Yellowstone - Security Events'
    category: 'Yellowstone'
    query: '''
YellowstoneSecurityEvents_CL
| where Severity in ("High", "Critical")
| summarize Count = count() by EventType, ThreatLevel
| sort by Count desc
    '''
    version: 2
  }
}

// Alert Rule - High Query Response Time
resource queryResponseTimeAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-high-query-response-time'
  location: location
  tags: tags
  properties: {
    displayName: 'Yellowstone - High Query Response Time'
    description: 'Triggered when average query response time exceeds 5 seconds'
    severity: 2
    enabled: true
    scopes: [
      logAnalyticsWorkspaceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: '''
YellowstoneQueryPerformance_CL
| summarize AvgTimeMs = avg(ExecutionTimeMs) by bin(TimeGenerated, 5m)
| where AvgTimeMs > 5000
          '''
          timeAggregation: 'Average'
          operator: 'GreaterThan'
          threshold: 5000
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: []
    }
  }
}

// Alert Rule - Security Event
resource securityEventAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-security-threat'
  location: location
  tags: tags
  properties: {
    displayName: 'Yellowstone - Security Threat Detected'
    description: 'Triggered when high/critical security events are detected'
    severity: 1
    enabled: true
    scopes: [
      logAnalyticsWorkspaceId
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: '''
YellowstoneSecurityEvents_CL
| where Severity in ("High", "Critical")
| summarize Count = count()
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: []
    }
  }
}

// Alert Rule - Query Failures
resource queryFailureAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-query-failures'
  location: location
  tags: tags
  properties: {
    displayName: 'Yellowstone - Elevated Query Failure Rate'
    description: 'Triggered when query failure rate exceeds 5%'
    severity: 2
    enabled: true
    scopes: [
      logAnalyticsWorkspaceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: '''
YellowstoneQueryPerformance_CL
| summarize
    TotalQueries = count(),
    FailedQueries = countif(Status == "Error")
| extend FailureRate = (todouble(FailedQueries) / TotalQueries) * 100
| where FailureRate > 5
          '''
          timeAggregation: 'Average'
          operator: 'GreaterThan'
          threshold: 5
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: []
    }
  }
}

// Output
output dataCollectionRuleId string = dataCollectionRule.id
output auditLogsTableName string = auditLogsTable.name
output queryPerformanceTableName string = queryPerformanceTable.name
output securityEventsTableName string = securityEventsTable.name
