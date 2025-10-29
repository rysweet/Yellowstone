"""
Curated benchmark queries for performance testing.

This module provides 50+ carefully designed benchmark queries covering:
- Simple queries (1 hop)
- Medium complexity (2-3 hops)
- Complex queries (4+ hops, aggregations)
- Real security investigation patterns
- Variable-length paths
- Edge cases and stress tests
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QueryComplexity(Enum):
    """Classification of query complexity."""

    SIMPLE = "simple"  # 1 hop, basic filters
    MEDIUM = "medium"  # 2-3 hops, joins
    COMPLEX = "complex"  # 4+ hops, aggregations
    STRESS = "stress"  # Variable-length, heavy computation


@dataclass
class BenchmarkQuery:
    """Represents a single benchmark query.

    Attributes:
        id: Unique identifier for the query
        name: Human-readable name
        cypher: Cypher query string
        kql: Equivalent native KQL query for comparison
        complexity: Query complexity level
        category: Query category (e.g., 'security', 'relationships')
        description: What the query does
        expected_result_count: Expected number of results (for validation)
        tags: List of tags for filtering (e.g., ['aggregation', 'path'])
    """

    id: str
    name: str
    cypher: str
    kql: str
    complexity: QueryComplexity
    category: str
    description: str
    expected_result_count: Optional[int] = None
    tags: list[str] = None

    def __post_init__(self) -> None:
        """Initialize default tags."""
        if self.tags is None:
            self.tags = []


class BenchmarkQueries:
    """Collection of curated benchmark queries.

    Provides 50+ benchmark queries organized by complexity and category.
    """

    def __init__(self) -> None:
        """Initialize the benchmark query collection."""
        self._queries = self._create_queries()

    def _create_queries(self) -> list[BenchmarkQuery]:
        """Create the full benchmark query suite.

        Returns:
            List of 50+ benchmark queries
        """
        queries = []

        # ====================================================================
        # SIMPLE QUERIES (1 hop, basic filters)
        # ====================================================================

        queries.append(
            BenchmarkQuery(
                id="simple_001",
                name="Find user by name",
                cypher="MATCH (u:User {name: 'admin'}) RETURN u",
                kql="SecurityAlert | where UserName == 'admin' | project UserName, TimeGenerated",
                complexity=QueryComplexity.SIMPLE,
                category="user_lookup",
                description="Find specific user by exact name match",
                expected_result_count=1,
                tags=["filter", "single_node"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_002",
                name="Find all high severity alerts",
                cypher="MATCH (a:Alert) WHERE a.severity = 'High' RETURN a",
                kql="SecurityAlert | where AlertSeverity == 'High' | project AlertName, TimeGenerated",
                complexity=QueryComplexity.SIMPLE,
                category="alerts",
                description="Filter alerts by severity level",
                expected_result_count=None,
                tags=["filter", "severity"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_003",
                name="Count all users",
                cypher="MATCH (u:User) RETURN COUNT(u) as user_count",
                kql="SecurityAlert | summarize UserCount = dcount(UserName)",
                complexity=QueryComplexity.SIMPLE,
                category="aggregation",
                description="Simple count aggregation",
                expected_result_count=1,
                tags=["aggregation", "count"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_004",
                name="Find recent alerts",
                cypher="MATCH (a:Alert) WHERE a.timestamp > '2024-01-01' RETURN a LIMIT 10",
                kql="SecurityAlert | where TimeGenerated > datetime(2024-01-01) | take 10",
                complexity=QueryComplexity.SIMPLE,
                category="alerts",
                description="Time-based filtering with limit",
                expected_result_count=10,
                tags=["filter", "time", "limit"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_005",
                name="List distinct alert types",
                cypher="MATCH (a:Alert) RETURN DISTINCT a.type",
                kql="SecurityAlert | distinct AlertType",
                complexity=QueryComplexity.SIMPLE,
                category="alerts",
                description="Distinct value enumeration",
                expected_result_count=None,
                tags=["distinct", "projection"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_006",
                name="Find alerts by IP",
                cypher="MATCH (a:Alert) WHERE a.source_ip = '192.168.1.100' RETURN a",
                kql="SecurityAlert | where SourceIP == '192.168.1.100'",
                complexity=QueryComplexity.SIMPLE,
                category="network",
                description="IP-based alert lookup",
                expected_result_count=None,
                tags=["filter", "network"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_007",
                name="Top 10 users by alert count",
                cypher="MATCH (u:User)<-[:TRIGGERED]-(a:Alert) RETURN u.name, COUNT(a) as alert_count ORDER BY alert_count DESC LIMIT 10",
                kql="SecurityAlert | summarize AlertCount = count() by UserName | top 10 by AlertCount desc",
                complexity=QueryComplexity.SIMPLE,
                category="aggregation",
                description="Aggregation with ordering and limit",
                expected_result_count=10,
                tags=["aggregation", "order", "limit"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_008",
                name="Find hosts with malware",
                cypher="MATCH (h:Host)-[:HAS_ALERT]->(a:Alert) WHERE a.type = 'Malware' RETURN h",
                kql="SecurityAlert | where AlertType == 'Malware' | project ComputerName, TimeGenerated",
                complexity=QueryComplexity.SIMPLE,
                category="security",
                description="Single-hop relationship with filter",
                expected_result_count=None,
                tags=["relationship", "security"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_009",
                name="Average alert severity score",
                cypher="MATCH (a:Alert) RETURN AVG(a.severity_score) as avg_severity",
                kql="SecurityAlert | summarize AvgSeverity = avg(AlertSeverity)",
                complexity=QueryComplexity.SIMPLE,
                category="aggregation",
                description="Average aggregation function",
                expected_result_count=1,
                tags=["aggregation", "average"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="simple_010",
                name="Find failed login attempts",
                cypher="MATCH (e:Event) WHERE e.type = 'FailedLogin' RETURN e",
                kql="SigninLogs | where ResultType != '0' | project UserPrincipalName, TimeGenerated",
                complexity=QueryComplexity.SIMPLE,
                category="authentication",
                description="Filter authentication events",
                expected_result_count=None,
                tags=["filter", "authentication"],
            )
        )

        # ====================================================================
        # MEDIUM COMPLEXITY QUERIES (2-3 hops, joins)
        # ====================================================================

        queries.append(
            BenchmarkQuery(
                id="medium_001",
                name="User to alert to host path",
                cypher="MATCH (u:User)-[:TRIGGERED]->(a:Alert)<-[:HAS_ALERT]-(h:Host) RETURN u, a, h",
                kql="""SecurityAlert
| join kind=inner (DeviceInfo | project DeviceId, ComputerName) on $left.SystemAlertId == $right.DeviceId
| project UserName, AlertName, ComputerName""",
                complexity=QueryComplexity.MEDIUM,
                category="relationships",
                description="2-hop path through alerts",
                expected_result_count=None,
                tags=["path", "join"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_002",
                name="Lateral movement detection",
                cypher="MATCH (h1:Host)-[:CONNECTS_TO]->(h2:Host)-[:CONNECTS_TO]->(h3:Host) WHERE h1 <> h3 RETURN h1, h2, h3",
                kql="""DeviceNetworkEvents
| where ActionType == 'ConnectionSuccess'
| join kind=inner (DeviceNetworkEvents | where ActionType == 'ConnectionSuccess') on $left.RemoteIP == $right.LocalIP
| project SourceHost=DeviceName, PivotHost=DeviceName1, TargetHost=RemoteIP""",
                complexity=QueryComplexity.MEDIUM,
                category="security",
                description="Detect 3-hop lateral movement",
                expected_result_count=None,
                tags=["path", "security", "lateral_movement"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_003",
                name="Users with multiple alert types",
                cypher="MATCH (u:User)-[:TRIGGERED]->(a:Alert) WITH u, COUNT(DISTINCT a.type) as alert_types WHERE alert_types > 3 RETURN u, alert_types",
                kql="""SecurityAlert
| summarize AlertTypes = dcount(AlertType) by UserName
| where AlertTypes > 3""",
                complexity=QueryComplexity.MEDIUM,
                category="aggregation",
                description="Aggregate with filter on aggregated value",
                expected_result_count=None,
                tags=["aggregation", "filter", "distinct"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_004",
                name="Alert correlation by time window",
                cypher="""MATCH (a1:Alert)-[:SAME_HOST]->(a2:Alert)
WHERE abs(a1.timestamp - a2.timestamp) < 300
RETURN a1, a2""",
                kql="""SecurityAlert
| join kind=inner (SecurityAlert) on ComputerName
| where abs(datetime_diff('second', TimeGenerated, TimeGenerated1)) < 300
| project Alert1=AlertName, Alert2=AlertName1, TimeDiff=datetime_diff('second', TimeGenerated, TimeGenerated1)""",
                complexity=QueryComplexity.MEDIUM,
                category="correlation",
                description="Correlate alerts within 5-minute window",
                expected_result_count=None,
                tags=["correlation", "time", "join"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_005",
                name="Find compromised accounts",
                cypher="""MATCH (u:User)-[:TRIGGERED]->(a:Alert)
WHERE a.type IN ['SuspiciousLogin', 'DataExfiltration']
WITH u, COLLECT(a.type) as alert_types
WHERE SIZE(alert_types) >= 2
RETURN u, alert_types""",
                kql="""SecurityAlert
| where AlertType in ('SuspiciousLogin', 'DataExfiltration')
| summarize AlertTypes = make_set(AlertType) by UserName
| where array_length(AlertTypes) >= 2""",
                complexity=QueryComplexity.MEDIUM,
                category="security",
                description="Multi-indicator compromise detection",
                expected_result_count=None,
                tags=["security", "aggregation", "collection"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_006",
                name="Network communication patterns",
                cypher="""MATCH (h1:Host)-[c:CONNECTS_TO]->(h2:Host)
WITH h1, h2, COUNT(c) as connection_count
WHERE connection_count > 100
RETURN h1.name, h2.name, connection_count
ORDER BY connection_count DESC""",
                kql="""DeviceNetworkEvents
| summarize ConnectionCount = count() by SourceHost=DeviceName, TargetHost=RemoteIP
| where ConnectionCount > 100
| order by ConnectionCount desc""",
                complexity=QueryComplexity.MEDIUM,
                category="network",
                description="High-volume connection analysis",
                expected_result_count=None,
                tags=["aggregation", "network", "filter"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_007",
                name="User behavior baseline deviation",
                cypher="""MATCH (u:User)-[:PERFORMED]->(a:Action)
WITH u, COUNT(a) as action_count, AVG(a.risk_score) as avg_risk
WHERE action_count > 50 AND avg_risk > 0.7
RETURN u, action_count, avg_risk""",
                kql="""AuditLogs
| summarize ActionCount = count(), AvgRisk = avg(RiskScore) by UserPrincipalName
| where ActionCount > 50 and AvgRisk > 0.7""",
                complexity=QueryComplexity.MEDIUM,
                category="behavior",
                description="Anomalous user behavior detection",
                expected_result_count=None,
                tags=["aggregation", "behavior", "anomaly"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_008",
                name="Process parent-child chains",
                cypher="""MATCH (p1:Process)-[:SPAWNED]->(p2:Process)-[:SPAWNED]->(p3:Process)
WHERE p3.name = 'powershell.exe'
RETURN p1, p2, p3""",
                kql="""DeviceProcessEvents
| where FileName == 'powershell.exe'
| join kind=inner (DeviceProcessEvents) on $left.InitiatingProcessId == $right.ProcessId
| join kind=inner (DeviceProcessEvents) on $left.InitiatingProcessId1 == $right.ProcessId
| project GrandParent=FileName, Parent=FileName1, Child=FileName2""",
                complexity=QueryComplexity.MEDIUM,
                category="security",
                description="3-level process tree analysis",
                expected_result_count=None,
                tags=["path", "process", "security"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_009",
                name="File access by multiple users",
                cypher="""MATCH (u:User)-[:ACCESSED]->(f:File)
WITH f, COLLECT(DISTINCT u.name) as users
WHERE SIZE(users) > 5
RETURN f.path, users, SIZE(users) as user_count""",
                kql="""DeviceFileEvents
| summarize Users = make_set(InitiatingProcessAccountName) by FileName, FolderPath
| where array_length(Users) > 5
| project FilePath = strcat(FolderPath, '/', FileName), Users, UserCount = array_length(Users)""",
                complexity=QueryComplexity.MEDIUM,
                category="file_access",
                description="Shared file access patterns",
                expected_result_count=None,
                tags=["aggregation", "collection", "file"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="medium_010",
                name="Alert clustering by host",
                cypher="""MATCH (h:Host)-[:HAS_ALERT]->(a:Alert)
WITH h, a.type as alert_type, COUNT(*) as count
RETURN h.name, COLLECT({type: alert_type, count: count}) as alert_distribution""",
                kql="""SecurityAlert
| summarize AlertDistribution = make_bag(pack(AlertType, count())) by ComputerName
| project ComputerName, AlertDistribution""",
                complexity=QueryComplexity.MEDIUM,
                category="aggregation",
                description="Alert type distribution per host",
                expected_result_count=None,
                tags=["aggregation", "collection", "grouping"],
            )
        )

        # ====================================================================
        # COMPLEX QUERIES (4+ hops, heavy aggregations)
        # ====================================================================

        queries.append(
            BenchmarkQuery(
                id="complex_001",
                name="Attack path reconstruction",
                cypher="""MATCH path = (u:User)-[:TRIGGERED]->(a1:Alert)-[:RELATED_TO]->(a2:Alert)
                -[:AFFECTS]->(h:Host)-[:CONTAINS]->(f:File)
WHERE a1.severity = 'High'
RETURN path""",
                kql="""SecurityAlert
| where AlertSeverity == 'High'
| join kind=inner (SecurityAlert) on SystemAlertId
| join kind=inner (DeviceInfo) on ComputerName
| join kind=inner (DeviceFileEvents) on DeviceId
| project UserName, Alert1=AlertName, Alert2=AlertName1, ComputerName, FileName""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="4-hop attack kill chain reconstruction",
                expected_result_count=None,
                tags=["path", "security", "kill_chain"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_002",
                name="Multi-stage lateral movement",
                cypher="""MATCH path = (h1:Host)-[:CONNECTS_TO*2..4]->(h2:Host)
WHERE h1.name = 'entry-point' AND h2.name CONTAINS 'dc-'
RETURN path, LENGTH(path) as hop_count""",
                kql="""let EntryPoint = 'entry-point';
DeviceNetworkEvents
| where DeviceName == EntryPoint
| mv-expand RemoteIP
| join kind=inner (DeviceNetworkEvents) on $left.RemoteIP == $right.LocalIP
| join kind=inner (DeviceNetworkEvents) on $left.RemoteIP1 == $right.LocalIP
| where DeviceName2 contains 'dc-'
| project Path = strcat(DeviceName, ' -> ', DeviceName1, ' -> ', DeviceName2), HopCount = 3""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="Variable-length path lateral movement",
                expected_result_count=None,
                tags=["path", "variable_length", "security"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_003",
                name="Insider threat detection",
                cypher="""MATCH (u:User)-[:PERFORMED]->(a:Action)-[:ON]->(r:Resource)
WHERE r.classification = 'Sensitive'
WITH u, COUNT(DISTINCT r) as resource_count,
     COUNT(a) as action_count,
     COLLECT(DISTINCT a.type) as action_types
WHERE resource_count > 10 AND SIZE(action_types) > 3
RETURN u, resource_count, action_count, action_types
ORDER BY resource_count DESC""",
                kql="""AuditLogs
| where ResourceClassification == 'Sensitive'
| summarize ResourceCount = dcount(Resource),
            ActionCount = count(),
            ActionTypes = make_set(ActivityType) by UserPrincipalName
| where ResourceCount > 10 and array_length(ActionTypes) > 3
| order by ResourceCount desc""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="Complex insider threat behavior pattern",
                expected_result_count=None,
                tags=["aggregation", "security", "insider_threat"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_004",
                name="Privilege escalation chains",
                cypher="""MATCH (u:User)-[:HAS_ROLE]->(r1:Role)-[:GRANTS*1..3]->(r2:Role)
WHERE r2.privileged = true AND u.is_service_account = false
RETURN u, r1, r2, LENGTH([(r1)-[:GRANTS*]->(r2) | r1]) as escalation_steps""",
                kql="""IdentityInfo
| where IsServiceAccount == false
| join kind=inner (RoleAssignments) on UserPrincipalName
| join kind=inner (RolePermissions | where IsPrivileged == true) on RoleName
| extend EscalationSteps = 1
| project UserPrincipalName, SourceRole=RoleName, TargetRole=RoleName1, EscalationSteps""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="Multi-hop privilege escalation detection",
                expected_result_count=None,
                tags=["path", "security", "privilege"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_005",
                name="Data exfiltration pattern",
                cypher="""MATCH (u:User)-[:ACCESSED]->(f:File)-[:COPIED_TO]->(e:ExternalLocation)
WHERE f.size > 10000000
WITH u, COUNT(f) as file_count, SUM(f.size) as total_size,
     COLLECT(DISTINCT e.domain) as destinations
WHERE file_count > 5 AND SIZE(destinations) > 1
RETURN u, file_count, total_size, destinations""",
                kql="""DeviceFileEvents
| where ActionType in ('FileCopiedToRemoteLocation', 'FileUploaded')
| where FileSize > 10000000
| summarize FileCount = count(),
            TotalSize = sum(FileSize),
            Destinations = make_set(RemoteUrl) by InitiatingProcessAccountName
| where FileCount > 5 and array_length(Destinations) > 1""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="Data exfiltration behavior detection",
                expected_result_count=None,
                tags=["aggregation", "security", "exfiltration"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_006",
                name="Command and control detection",
                cypher="""MATCH (h:Host)-[c:CONNECTS_TO]->(ip:IPAddress)
WHERE ip.reputation_score < 30
WITH h, ip, COUNT(c) as connection_count,
     AVG(c.bytes_sent) as avg_bytes,
     stddev(c.interval) as regularity
WHERE connection_count > 10 AND regularity < 60
RETURN h, ip, connection_count, avg_bytes, regularity
ORDER BY regularity ASC""",
                kql="""DeviceNetworkEvents
| join kind=inner (ThreatIntelligenceIndicator | where ConfidenceScore < 30) on RemoteIP
| summarize ConnectionCount = count(),
            AvgBytes = avg(BytesSent),
            Regularity = stdev(TimeInterval) by DeviceName, RemoteIP
| where ConnectionCount > 10 and Regularity < 60
| order by Regularity asc""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="C2 beacon detection with statistical analysis",
                expected_result_count=None,
                tags=["aggregation", "security", "c2", "statistics"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_007",
                name="Attack graph centrality",
                cypher="""MATCH (h:Host)-[:CONNECTS_TO]->(target:Host)
WITH target, COUNT(DISTINCT h) as in_degree
MATCH (target)-[:CONNECTS_TO]->(h2:Host)
WITH target, in_degree, COUNT(DISTINCT h2) as out_degree
WHERE in_degree > 5 AND out_degree > 5
RETURN target.name, in_degree, out_degree, (in_degree + out_degree) as centrality
ORDER BY centrality DESC LIMIT 10""",
                kql="""let InDegree = DeviceNetworkEvents
| summarize InDegree = dcount(DeviceName) by Target=RemoteIP;
let OutDegree = DeviceNetworkEvents
| summarize OutDegree = dcount(RemoteIP) by Source=DeviceName;
InDegree
| join kind=inner OutDegree on $left.Target == $right.Source
| where InDegree > 5 and OutDegree > 5
| extend Centrality = InDegree + OutDegree
| top 10 by Centrality desc""",
                complexity=QueryComplexity.COMPLEX,
                category="graph_analysis",
                description="Network centrality calculation",
                expected_result_count=10,
                tags=["aggregation", "graph", "centrality"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_008",
                name="Temporal attack correlation",
                cypher="""MATCH (a1:Alert)-[:OCCURRED_ON]->(h:Host)
MATCH (a2:Alert)-[:OCCURRED_ON]->(h)
WHERE a1 <> a2
  AND abs(a1.timestamp - a2.timestamp) < 3600
  AND a1.type <> a2.type
WITH h, COLLECT({alert: a1.type, time: a1.timestamp}) as timeline
WHERE SIZE(timeline) >= 3
RETURN h, timeline, SIZE(timeline) as alert_count""",
                kql="""SecurityAlert
| join kind=inner (SecurityAlert) on ComputerName
| where SystemAlertId != SystemAlertId1
| where abs(datetime_diff('second', TimeGenerated, TimeGenerated1)) < 3600
| where AlertType != AlertType1
| summarize Timeline = make_list(pack('alert', AlertType, 'time', TimeGenerated)) by ComputerName
| where array_length(Timeline) >= 3
| extend AlertCount = array_length(Timeline)""",
                complexity=QueryComplexity.COMPLEX,
                category="correlation",
                description="Multi-alert temporal correlation",
                expected_result_count=None,
                tags=["correlation", "time", "aggregation"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_009",
                name="User risk scoring",
                cypher="""MATCH (u:User)-[:TRIGGERED]->(a:Alert)
OPTIONAL MATCH (u)-[:ACCESSED]->(r:Resource) WHERE r.classification = 'Sensitive'
WITH u,
     COUNT(DISTINCT a) as alert_count,
     SUM(a.severity_score) as total_severity,
     COUNT(DISTINCT r) as sensitive_access_count
RETURN u.name,
       alert_count,
       total_severity,
       sensitive_access_count,
       (alert_count * 10 + total_severity + sensitive_access_count * 5) as risk_score
ORDER BY risk_score DESC LIMIT 20""",
                kql="""let AlertScore = SecurityAlert
| summarize AlertCount = count(), TotalSeverity = sum(AlertSeverity) by UserName;
let SensitiveAccess = AuditLogs
| where ResourceClassification == 'Sensitive'
| summarize SensitiveAccessCount = count() by UserPrincipalName;
AlertScore
| join kind=leftouter SensitiveAccess on $left.UserName == $right.UserPrincipalName
| extend RiskScore = AlertCount * 10 + TotalSeverity + SensitiveAccessCount * 5
| top 20 by RiskScore desc""",
                complexity=QueryComplexity.COMPLEX,
                category="risk_analysis",
                description="Composite user risk scoring",
                expected_result_count=20,
                tags=["aggregation", "scoring", "risk"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="complex_010",
                name="Supply chain compromise detection",
                cypher="""MATCH (v:Vendor)-[:SUPPLIES]->(s:Software)-[:INSTALLED_ON]->(h:Host)
MATCH (h)-[:HAS_ALERT]->(a:Alert)
WHERE a.type IN ['Malware', 'SuspiciousProcess']
WITH v, s, COUNT(DISTINCT h) as affected_hosts, COLLECT(DISTINCT a.type) as alert_types
WHERE affected_hosts > 3
RETURN v.name, s.name, affected_hosts, alert_types
ORDER BY affected_hosts DESC""",
                kql="""let AffectedHosts = SecurityAlert
| where AlertType in ('Malware', 'SuspiciousProcess')
| join kind=inner (DeviceInfo) on ComputerName
| join kind=inner (DeviceTvmSoftwareInventory) on DeviceId
| summarize AffectedHosts = dcount(DeviceId),
            AlertTypes = make_set(AlertType) by Vendor, SoftwareName
| where AffectedHosts > 3;
AffectedHosts
| order by AffectedHosts desc""",
                complexity=QueryComplexity.COMPLEX,
                category="security",
                description="Supply chain attack pattern detection",
                expected_result_count=None,
                tags=["path", "security", "supply_chain"],
            )
        )

        # ====================================================================
        # STRESS QUERIES (Variable-length paths, heavy computation)
        # ====================================================================

        queries.append(
            BenchmarkQuery(
                id="stress_001",
                name="Deep path exploration",
                cypher="""MATCH path = (start:Host {name: 'entry'})-[:CONNECTS_TO*1..10]->(target:Host)
WHERE target.criticality = 'High'
RETURN path, LENGTH(path) as hops
ORDER BY hops ASC LIMIT 5""",
                kql="""// Variable-length path simulation via recursive CTE
let Entry = 'entry';
DeviceNetworkEvents
| where DeviceName == Entry
// This is a simplified version - full implementation requires graph operators
| project Source=DeviceName, Target=RemoteIP, Hops=1""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Variable-length path up to 10 hops",
                expected_result_count=5,
                tags=["variable_length", "path", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_002",
                name="All shortest paths",
                cypher="""MATCH path = allShortestPaths((source:Host {zone: 'DMZ'})-[:CONNECTS_TO*]->
                (target:Host {zone: 'Internal'}))
RETURN path, LENGTH(path) as hops""",
                kql="""// Shortest path calculation - requires graph operators
DeviceNetworkEvents
| where SourceZone == 'DMZ' and TargetZone == 'Internal'
// Full implementation requires specialized graph algorithms""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="All shortest paths between zones",
                expected_result_count=None,
                tags=["variable_length", "shortest_path", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_003",
                name="Community detection",
                cypher="""MATCH (h1:Host)-[:CONNECTS_TO]-(h2:Host)
WITH h1, COLLECT(DISTINCT h2) as neighbors
WHERE SIZE(neighbors) > 10
MATCH (n1) WHERE n1 IN neighbors
MATCH (n2) WHERE n2 IN neighbors AND n1 <> n2
MATCH (n1)-[:CONNECTS_TO]-(n2)
WITH h1, neighbors, COUNT(*) as internal_connections
RETURN h1.name, SIZE(neighbors) as degree,
       internal_connections,
       (internal_connections * 1.0 / (SIZE(neighbors) * (SIZE(neighbors) - 1))) as density""",
                kql="""let Neighbors = DeviceNetworkEvents
| summarize Neighbors = make_set(RemoteIP) by DeviceName
| where array_length(Neighbors) > 10;
// Community detection requires complex graph algorithms
Neighbors
| project DeviceName, Degree = array_length(Neighbors)""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Network community structure detection",
                expected_result_count=None,
                tags=["graph", "community", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_004",
                name="PageRank calculation",
                cypher="""MATCH (h:Host)
CALL gds.pageRank.stream({nodeProjection: 'Host', relationshipProjection: 'CONNECTS_TO'})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name as host, score
ORDER BY score DESC LIMIT 20""",
                kql="""// PageRank requires iterative computation - not native to KQL
DeviceNetworkEvents
| summarize InDegree = dcount(DeviceName), OutDegree = dcount(RemoteIP) by Node=DeviceName
| extend PageRankApprox = InDegree * 1.0 / (OutDegree + 1)
| top 20 by PageRankApprox desc""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="PageRank centrality calculation",
                expected_result_count=20,
                tags=["graph", "pagerank", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_005",
                name="Triangle counting",
                cypher="""MATCH (a:Host)-[:CONNECTS_TO]->(b:Host)-[:CONNECTS_TO]->(c:Host)-[:CONNECTS_TO]->(a)
RETURN COUNT(*) as triangle_count""",
                kql="""DeviceNetworkEvents
| join kind=inner (DeviceNetworkEvents) on $left.RemoteIP == $right.DeviceName
| join kind=inner (DeviceNetworkEvents) on $left.RemoteIP1 == $right.DeviceName and $left.DeviceName == $right.RemoteIP
| summarize TriangleCount = count()""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Count triangles in network graph",
                expected_result_count=1,
                tags=["graph", "triangle", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_006",
                name="Strongly connected components",
                cypher="""CALL gds.alpha.scc.stream({nodeProjection: 'Host', relationshipProjection: 'CONNECTS_TO'})
YIELD nodeId, componentId
RETURN componentId, COUNT(*) as component_size
ORDER BY component_size DESC""",
                kql="""// Strongly connected components - requires graph algorithms
DeviceNetworkEvents
| summarize ComponentSize = dcount(DeviceName) by ComponentId=1
// Full implementation requires specialized algorithms""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Find strongly connected components",
                expected_result_count=None,
                tags=["graph", "components", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_007",
                name="Graph diameter calculation",
                cypher="""MATCH (h1:Host), (h2:Host)
WHERE h1 <> h2
MATCH path = shortestPath((h1)-[:CONNECTS_TO*]-(h2))
RETURN MAX(LENGTH(path)) as diameter""",
                kql="""// Graph diameter - requires all-pairs shortest paths
// This is computationally expensive and not directly supported
DeviceNetworkEvents
| summarize by DeviceName, RemoteIP
// Full calculation requires specialized graph algorithms""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Calculate network graph diameter",
                expected_result_count=1,
                tags=["graph", "diameter", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_008",
                name="Betweenness centrality",
                cypher="""CALL gds.betweenness.stream({nodeProjection: 'Host', relationshipProjection: 'CONNECTS_TO'})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name as host, score
ORDER BY score DESC LIMIT 20""",
                kql="""// Betweenness centrality - requires all shortest paths
DeviceNetworkEvents
| summarize Connections = count() by DeviceName
| top 20 by Connections desc
| extend BetweennessApprox = Connections
// Full calculation requires path counting algorithms""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Calculate betweenness centrality",
                expected_result_count=20,
                tags=["graph", "centrality", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_009",
                name="Louvain community detection",
                cypher="""CALL gds.louvain.stream({nodeProjection: 'Host', relationshipProjection: 'CONNECTS_TO'})
YIELD nodeId, communityId
RETURN communityId, COUNT(*) as community_size,
       COLLECT(gds.util.asNode(nodeId).name) as members
ORDER BY community_size DESC""",
                kql="""// Louvain community detection - complex modularity optimization
DeviceNetworkEvents
| summarize Members = make_set(DeviceName) by CommunityId=hash(RemoteIP, 10)
| extend CommunitySize = array_length(Members)
| order by CommunitySize desc
// Full implementation requires iterative modularity calculation""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Louvain community detection algorithm",
                expected_result_count=None,
                tags=["graph", "community", "stress"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="stress_010",
                name="Full graph traversal",
                cypher="""MATCH (start:Host {name: 'root'})
CALL apoc.path.subgraphAll(start, {relationshipFilter: 'CONNECTS_TO', maxLevel: 5})
YIELD nodes, relationships
RETURN SIZE(nodes) as node_count, SIZE(relationships) as relationship_count""",
                kql="""// Full subgraph extraction - requires recursive traversal
let Root = 'root';
DeviceNetworkEvents
| where DeviceName == Root
// Full implementation requires recursive expansion
| summarize NodeCount = dcount(RemoteIP), RelationshipCount = count()""",
                complexity=QueryComplexity.STRESS,
                category="graph_analysis",
                description="Extract and count subgraph elements",
                expected_result_count=1,
                tags=["graph", "traversal", "stress"],
            )
        )

        # ====================================================================
        # ADDITIONAL REAL-WORLD SECURITY QUERIES
        # ====================================================================

        queries.append(
            BenchmarkQuery(
                id="security_001",
                name="Brute force attack detection",
                cypher="""MATCH (u:User)<-[:TARGETED]-(e:FailedLogin)
WHERE e.timestamp > datetime() - duration({hours: 1})
WITH u, COUNT(e) as failed_attempts
WHERE failed_attempts > 5
RETURN u.name, failed_attempts
ORDER BY failed_attempts DESC""",
                kql="""SigninLogs
| where TimeGenerated > ago(1h)
| where ResultType != '0'
| summarize FailedAttempts = count() by UserPrincipalName
| where FailedAttempts > 5
| order by FailedAttempts desc""",
                complexity=QueryComplexity.MEDIUM,
                category="security",
                description="Detect brute force login attempts",
                expected_result_count=None,
                tags=["security", "authentication", "brute_force"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="security_002",
                name="Credential dumping detection",
                cypher="""MATCH (p:Process)-[:ACCESSED]->(m:Memory)
WHERE p.name IN ['mimikatz.exe', 'procdump.exe', 'pwdump.exe']
   OR m.region CONTAINS 'lsass'
RETURN p, m""",
                kql="""DeviceProcessEvents
| where FileName in ('mimikatz.exe', 'procdump.exe', 'pwdump.exe')
   or ProcessCommandLine contains 'lsass'
| project DeviceName, FileName, ProcessCommandLine, TimeGenerated""",
                complexity=QueryComplexity.SIMPLE,
                category="security",
                description="Detect credential dumping tools",
                expected_result_count=None,
                tags=["security", "credential", "process"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="security_003",
                name="PowerShell obfuscation detection",
                cypher="""MATCH (p:Process)
WHERE p.name = 'powershell.exe'
  AND (p.command_line CONTAINS 'encodedcommand'
       OR p.command_line CONTAINS 'bypass'
       OR p.command_line CONTAINS 'hidden')
RETURN p""",
                kql="""DeviceProcessEvents
| where FileName =~ 'powershell.exe'
| where ProcessCommandLine contains 'encodedcommand'
    or ProcessCommandLine contains 'bypass'
    or ProcessCommandLine contains 'hidden'
| project DeviceName, ProcessCommandLine, TimeGenerated""",
                complexity=QueryComplexity.SIMPLE,
                category="security",
                description="Detect obfuscated PowerShell execution",
                expected_result_count=None,
                tags=["security", "powershell", "obfuscation"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="security_004",
                name="Living-off-the-land binaries",
                cypher="""MATCH (p:Process)
WHERE p.name IN ['certutil.exe', 'bitsadmin.exe', 'mshta.exe', 'regsvr32.exe']
  AND (p.command_line CONTAINS 'http' OR p.command_line CONTAINS 'download')
RETURN p""",
                kql="""DeviceProcessEvents
| where FileName in ('certutil.exe', 'bitsadmin.exe', 'mshta.exe', 'regsvr32.exe')
| where ProcessCommandLine contains 'http' or ProcessCommandLine contains 'download'
| project DeviceName, FileName, ProcessCommandLine, TimeGenerated""",
                complexity=QueryComplexity.SIMPLE,
                category="security",
                description="Detect LOLBin abuse for downloads",
                expected_result_count=None,
                tags=["security", "lolbin", "download"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="security_005",
                name="Ransomware file activity",
                cypher="""MATCH (p:Process)-[:MODIFIED]->(f:File)
WHERE f.extension IN ['.encrypted', '.locked', '.crypto']
WITH p, COUNT(DISTINCT f) as modified_files
WHERE modified_files > 50
RETURN p, modified_files
ORDER BY modified_files DESC""",
                kql="""DeviceFileEvents
| where ActionType == 'FileModified'
| where FileName endswith '.encrypted'
    or FileName endswith '.locked'
    or FileName endswith '.crypto'
| summarize ModifiedFiles = dcount(FileName) by InitiatingProcessFileName, DeviceName
| where ModifiedFiles > 50
| order by ModifiedFiles desc""",
                complexity=QueryComplexity.MEDIUM,
                category="security",
                description="Detect ransomware file encryption patterns",
                expected_result_count=None,
                tags=["security", "ransomware", "file"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="aggregation_001",
                name="Hourly alert distribution",
                cypher="""MATCH (a:Alert)
WHERE a.timestamp > datetime() - duration({days: 7})
WITH datetime({year: a.timestamp.year, month: a.timestamp.month,
               day: a.timestamp.day, hour: a.timestamp.hour}) as hour_bucket,
     COUNT(a) as alert_count
RETURN hour_bucket, alert_count
ORDER BY hour_bucket""",
                kql="""SecurityAlert
| where TimeGenerated > ago(7d)
| summarize AlertCount = count() by bin(TimeGenerated, 1h)
| order by TimeGenerated asc""",
                complexity=QueryComplexity.SIMPLE,
                category="aggregation",
                description="Time-bucketed alert distribution",
                expected_result_count=None,
                tags=["aggregation", "time", "distribution"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="aggregation_002",
                name="Percentile latency analysis",
                cypher="""MATCH (q:Query)
RETURN percentileCont(q.execution_time_ms, 0.50) as p50,
       percentileCont(q.execution_time_ms, 0.95) as p95,
       percentileCont(q.execution_time_ms, 0.99) as p99""",
                kql="""QueryPerformance
| summarize P50 = percentile(ExecutionTimeMs, 50),
            P95 = percentile(ExecutionTimeMs, 95),
            P99 = percentile(ExecutionTimeMs, 99)""",
                complexity=QueryComplexity.SIMPLE,
                category="aggregation",
                description="Calculate query latency percentiles",
                expected_result_count=1,
                tags=["aggregation", "percentile", "performance"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="aggregation_003",
                name="Moving average calculation",
                cypher="""MATCH (a:Alert)
WHERE a.timestamp > datetime() - duration({days: 30})
WITH datetime({year: a.timestamp.year, month: a.timestamp.month, day: a.timestamp.day}) as day,
     COUNT(a) as daily_count
ORDER BY day
RETURN day, daily_count,
       avg(daily_count) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as moving_avg_7d""",
                kql="""SecurityAlert
| where TimeGenerated > ago(30d)
| summarize DailyCount = count() by Day = bin(TimeGenerated, 1d)
| order by Day asc
| extend MovingAvg7d = row_window_session(DailyCount, Day, -6d, 0d, avg(DailyCount))""",
                complexity=QueryComplexity.MEDIUM,
                category="aggregation",
                description="7-day moving average of alerts",
                expected_result_count=None,
                tags=["aggregation", "time_series", "moving_average"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="security_006",
                name="Kerberoasting detection",
                cypher="""MATCH (u:User)-[:REQUESTED]->(t:Ticket)
WHERE t.encryption_type IN ['RC4', 'DES'] AND t.service_account = true
WITH u, COUNT(t) as suspicious_tickets
WHERE suspicious_tickets > 3
RETURN u.name, suspicious_tickets
ORDER BY suspicious_tickets DESC""",
                kql="""SecurityEvent
| where EventID == 4769
| where TicketEncryptionType in ('0x17', '0x03')
| where ServiceName endswith '$' == false
| summarize SuspiciousTickets = count() by TargetUserName
| where SuspiciousTickets > 3
| order by SuspiciousTickets desc""",
                complexity=QueryComplexity.MEDIUM,
                category="security",
                description="Detect Kerberoasting ticket requests",
                expected_result_count=None,
                tags=["security", "kerberos", "authentication"],
            )
        )

        queries.append(
            BenchmarkQuery(
                id="network_001",
                name="Beaconing detection via intervals",
                cypher="""MATCH (h:Host)-[c:CONNECTS_TO]->(ip:ExternalIP)
WITH h, ip, COLLECT(c.timestamp) as timestamps
WITH h, ip, timestamps,
     [i IN RANGE(0, SIZE(timestamps)-2) |
      duration.between(timestamps[i], timestamps[i+1]).milliseconds] as intervals
WITH h, ip, AVG(intervals) as avg_interval, stddev(intervals) as interval_stddev
WHERE interval_stddev < (avg_interval * 0.1)
RETURN h.name, ip.address, avg_interval, interval_stddev
ORDER BY interval_stddev ASC""",
                kql="""DeviceNetworkEvents
| where RemoteIPType == 'External'
| order by DeviceName, RemoteIP, TimeGenerated asc
| extend PrevTime = prev(TimeGenerated, 1)
| extend Interval = datetime_diff('millisecond', TimeGenerated, PrevTime)
| where isnotnull(Interval)
| summarize AvgInterval = avg(Interval), StdDevInterval = stdev(Interval) by DeviceName, RemoteIP
| where StdDevInterval < (AvgInterval * 0.1)
| order by StdDevInterval asc""",
                complexity=QueryComplexity.COMPLEX,
                category="network",
                description="Detect regular beaconing patterns via interval analysis",
                expected_result_count=None,
                tags=["network", "c2", "beaconing", "statistics"],
            )
        )

        return queries

    def get_all(self) -> list[BenchmarkQuery]:
        """Get all benchmark queries.

        Returns:
            List of all benchmark queries
        """
        return self._queries

    def get_by_complexity(self, complexity: QueryComplexity) -> list[BenchmarkQuery]:
        """Filter queries by complexity level.

        Args:
            complexity: Complexity level to filter by

        Returns:
            List of queries matching the complexity level
        """
        return [q for q in self._queries if q.complexity == complexity]

    def get_by_category(self, category: str) -> list[BenchmarkQuery]:
        """Filter queries by category.

        Args:
            category: Category to filter by

        Returns:
            List of queries in the specified category
        """
        return [q for q in self._queries if q.category == category]

    def get_by_tags(self, tags: list[str]) -> list[BenchmarkQuery]:
        """Filter queries by tags (any match).

        Args:
            tags: List of tags to filter by

        Returns:
            List of queries that have at least one matching tag
        """
        return [q for q in self._queries if any(tag in q.tags for tag in tags)]

    def get_by_id(self, query_id: str) -> Optional[BenchmarkQuery]:
        """Get a specific query by ID.

        Args:
            query_id: Query ID to look up

        Returns:
            BenchmarkQuery if found, None otherwise
        """
        for query in self._queries:
            if query.id == query_id:
                return query
        return None

    def get_summary(self) -> dict:
        """Get summary statistics about the benchmark suite.

        Returns:
            Dictionary with counts by complexity and category
        """
        summary = {
            "total_queries": len(self._queries),
            "by_complexity": {},
            "by_category": {},
        }

        for complexity in QueryComplexity:
            count = len(self.get_by_complexity(complexity))
            summary["by_complexity"][complexity.value] = count

        categories = set(q.category for q in self._queries)
        for category in categories:
            count = len(self.get_by_category(category))
            summary["by_category"][category] = count

        return summary
