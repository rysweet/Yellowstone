"""
Example usage scenarios for Agentic AI Translation Layer API.

Demonstrates:
- Basic translation requests
- Advanced options and optimization
- Batch translation
- Feedback loop
- Error handling
- Async patterns
"""

import asyncio
from typing import List, Optional
from datetime import datetime
import json


# ============================================================================
# Client Library (Example Implementation)
# ============================================================================

class AgenticTranslatorClient:
    """
    Client for Agentic AI Translation Layer API.

    Example usage:
        client = AgenticTranslatorClient(api_key="...")
        result = await client.translate(cypher, context)
    """

    def __init__(
        self,
        base_url: str = "https://api.cypher-sentinel.azure.com/v1",
        api_key: str = None
    ):
        self.base_url = base_url
        self.api_key = api_key

    async def translate(
        self,
        cypher: str,
        context: dict,
        options: Optional[dict] = None
    ) -> dict:
        """
        Translate Cypher query to KQL.

        Args:
            cypher: Cypher query string
            context: Translation context (schema, stats, etc.)
            options: Translation options (optimization goals, etc.)

        Returns:
            TranslationResponse dict
        """
        # Implementation would use httpx or aiohttp
        # This is a placeholder showing the API contract
        pass

    async def translate_batch(
        self,
        queries: List[dict],
        batch_options: Optional[dict] = None
    ) -> dict:
        """Batch translate multiple queries."""
        pass

    async def get_translation_status(
        self,
        translation_id: str
    ) -> dict:
        """Get async translation job status."""
        pass

    async def validate(
        self,
        cypher: str,
        kql: str,
        context: dict
    ) -> dict:
        """Validate semantic equivalence."""
        pass

    async def optimize(
        self,
        kql: str,
        cypher: Optional[str] = None,
        context: Optional[dict] = None,
        optimization_goals: Optional[List[str]] = None
    ) -> dict:
        """Optimize existing KQL query."""
        pass

    async def submit_feedback(
        self,
        translation_id: str,
        rating: int,
        correctness: bool,
        actual_execution_time_ms: Optional[float] = None,
        actual_result_count: Optional[int] = None,
        issues: Optional[List[str]] = None,
        comments: Optional[str] = None
    ) -> None:
        """Submit feedback on translation quality."""
        pass

    async def get_pattern_cache(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100
    ) -> dict:
        """Get cached translation patterns."""
        pass


# ============================================================================
# Example 1: Basic Translation
# ============================================================================

async def example_basic_translation():
    """
    Basic translation of a complex Cypher query.

    Use case: Security analyst investigating indirect access paths
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    # Complex Cypher query with multiple relationship types and negation
    cypher = """
    MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*1..4]->(r:Resource)
    WHERE r.classification = "secret"
      AND NOT (u)-[:DIRECT_PERMISSION]->(r)
    RETURN u.name, length(path) as indirection_depth
    ORDER BY indirection_depth
    LIMIT 50
    """

    # Translation context
    context = {
        "schema_version": "1.2.0",
        "schema_metadata": {
            "User": {
                "type": "node",
                "table_name": "Users",
                "cardinality": 50000,
                "indexed_fields": ["UserId", "Name", "Department"]
            },
            "Resource": {
                "type": "node",
                "table_name": "Resources",
                "cardinality": 10000,
                "indexed_fields": ["ResourceId", "Classification"]
            },
            "PERMISSION": {
                "type": "edge",
                "table_name": "Permissions",
                "cardinality": 200000,
                "average_degree": 4.0
            },
            "GROUP_MEMBER": {
                "type": "edge",
                "table_name": "GroupMemberships",
                "cardinality": 75000,
                "average_degree": 1.5
            }
        },
        "max_depth": 4,
        "performance_profile": "interactive"
    }

    # Translation options
    options = {
        "optimization_goal": "latency",
        "max_iterations": 3,
        "confidence_threshold": 0.85,
        "include_alternatives": True
    }

    # Execute translation
    result = await client.translate(cypher, context, options)

    print("Translation Result:")
    print(f"  Status: {result['status']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Strategy: {result['strategy']}")
    print(f"\nGenerated KQL:")
    print(result['kql_query'])
    print(f"\nEstimated Performance:")
    print(f"  Execution time: {result['estimated_performance']['execution_time_ms']}ms")
    print(f"  Result count: {result['estimated_performance']['result_cardinality']}")
    print(f"\nExplanation:")
    print(result['explanation'])

    # Check for warnings
    if 'warnings' in result:
        print(f"\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")

    # Review alternative strategies
    if 'alternatives' in result and result['alternatives']:
        print(f"\nAlternative Strategies:")
        for alt in result['alternatives']:
            print(f"  - {alt['strategy']} (confidence: {alt['confidence']})")
            print(f"    {alt['tradeoff']}")

    return result


# ============================================================================
# Example 2: Async Translation (Long-Running Query)
# ============================================================================

async def example_async_translation():
    """
    Async translation for complex queries that take longer.

    Use case: Attack path analysis with deep traversal
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    cypher = """
    MATCH path = (entry:Event {type: "InitialAccess"})
                 -[:CAUSED|:ENABLED*]->(outcome:Event)
    WHERE outcome.timestamp - entry.timestamp < duration('P1D')
      AND ALL(event IN nodes(path) WHERE event.detected = false)
    RETURN path, length(path) as chain_length
    ORDER BY chain_length DESC
    """

    context = {
        "schema_version": "1.2.0",
        "max_depth": 10,
        "performance_profile": "batch"
    }

    # Enable async mode for complex query
    options = {
        "async_mode": True,
        "max_iterations": 5
    }

    # Submit translation job
    job = await client.translate(cypher, context, options)

    print(f"Translation job submitted: {job['job_id']}")
    print(f"Status: {job['status']}")

    # Poll for completion
    while job['status'] in ['queued', 'processing']:
        await asyncio.sleep(1)
        job = await client.get_translation_status(job['job_id'])
        print(f"Progress: {job.get('progress', 0) * 100:.1f}% - {job.get('current_step', 'Unknown')}")

    if job['status'] == 'completed':
        result = job['result']
        print(f"\nTranslation completed!")
        print(f"KQL Query:\n{result['kql_query']}")
    else:
        error = job['error']
        print(f"\nTranslation failed: {error['reason']}")
        if 'suggested_alternative' in error:
            print(f"Suggested alternative: {error['suggested_alternative']}")


# ============================================================================
# Example 3: Batch Translation
# ============================================================================

async def example_batch_translation():
    """
    Batch translate multiple queries in parallel.

    Use case: Preprocessing a workload or testing coverage
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    # List of queries to translate
    queries = [
        {
            "cypher": "MATCH (u:User)-[:OWNS]->(d:Device) WHERE u.dept = 'IT' RETURN u.name, d.hostname",
            "context": {"schema_version": "1.2.0"},
            "options": {"optimization_goal": "latency"}
        },
        {
            "cypher": "MATCH (u:User)-[:LOGGED_INTO*1..3]->(d:Device) RETURN u.name, count(d)",
            "context": {"schema_version": "1.2.0", "max_depth": 3},
            "options": {"optimization_goal": "latency"}
        },
        {
            "cypher": "MATCH (d:Device)-[:CONNECTS_TO]->(n:Network) WHERE n.zone = 'DMZ' RETURN d.hostname",
            "context": {"schema_version": "1.2.0"},
            "options": {"optimization_goal": "throughput"}
        }
    ]

    # Batch options
    batch_options = {
        "parallel_execution": True,
        "fail_fast": False,
        "priority": "normal"
    }

    # Execute batch translation
    batch_result = await client.translate_batch(queries, batch_options)

    print(f"Batch Translation Results:")
    print(f"  Batch ID: {batch_result['batch_id']}")
    print(f"  Total: {batch_result['summary']['total']}")
    print(f"  Successful: {batch_result['summary']['successful']}")
    print(f"  Failed: {batch_result['summary']['failed']}")
    print(f"  Avg Confidence: {batch_result['summary']['avg_confidence']:.2f}")
    print(f"  Total Time: {batch_result['summary']['total_time_ms']}ms")

    print("\nIndividual Results:")
    for i, result in enumerate(batch_result['results']):
        print(f"\n  Query {i + 1}:")
        print(f"    Status: {result['status']}")
        print(f"    Confidence: {result.get('confidence', 'N/A')}")
        print(f"    Strategy: {result.get('strategy', 'N/A')}")


# ============================================================================
# Example 4: Optimization of Existing KQL
# ============================================================================

async def example_optimize_existing_kql():
    """
    Optimize existing KQL query using AI insights.

    Use case: Improving performance of manually written or fast-path translated KQL
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    # Original Cypher (for context)
    cypher = """
    MATCH (u:User)-[:OWNS]->(d:Device)-[:CONNECTS_TO]->(n:Network)
    WHERE u.department = "IT" AND n.security_zone = "DMZ"
    RETURN u.name, d.hostname, n.name
    """

    # Existing KQL (from direct translator or manual)
    existing_kql = """
    Users
    | where Department == "IT"
    | join kind=inner (DeviceOwnership) on UserId
    | join kind=inner (Devices) on DeviceId
    | join kind=inner (NetworkConnections) on DeviceId
    | join kind=inner (Networks) on NetworkId
    | where SecurityZone == "DMZ"
    | project UserName = Name, DeviceHostname = Hostname, NetworkName = NetworkName
    """

    context = {
        "schema_version": "1.2.0",
        "schema_metadata": {
            "Users": {"cardinality": 50000},
            "Devices": {"cardinality": 100000},
            "Networks": {"cardinality": 500}
        }
    }

    optimization_goals = ["latency", "cost"]

    # Optimize
    result = await client.optimize(
        kql=existing_kql,
        cypher=cypher,
        context=context,
        optimization_goals=optimization_goals
    )

    print("Optimization Result:")
    print(f"\nOriginal KQL:")
    print(result['original_kql'])
    print(f"\nOptimized KQL:")
    print(result['optimized_kql'])
    print(f"\nImprovements:")
    for improvement in result['improvements']:
        print(f"  - {improvement['type']}: {improvement['description']} (impact: {improvement['impact']})")
    print(f"\nEstimated Speedup: {result['estimated_speedup']:.2f}x")


# ============================================================================
# Example 5: Semantic Validation
# ============================================================================

async def example_semantic_validation():
    """
    Validate that KQL translation is semantically equivalent to Cypher.

    Use case: Verifying translation correctness before production use
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    cypher = """
    MATCH (u:User)-[:OWNS]->(d:Device)
    WHERE u.department = "IT"
    RETURN u.name, d.hostname
    """

    kql = """
    Users
    | where Department == "IT"
    | join kind=inner (DeviceOwnership) on UserId
    | join kind=inner (Devices) on DeviceId
    | project UserName = Name, DeviceHostname = Hostname
    """

    context = {
        "schema_version": "1.2.0"
    }

    # Validate
    validation = await client.validate(cypher, kql, context)

    print("Validation Result:")
    print(f"  Is Equivalent: {validation['is_equivalent']}")
    print(f"  Confidence: {validation['confidence']}")

    if not validation['is_equivalent']:
        print(f"\n  Differences Found:")
        for diff in validation['differences']:
            print(f"    - {diff['aspect']}: {diff['description']} (severity: {diff['severity']})")

    print(f"\n  Recommendation: {validation['recommendation']}")


# ============================================================================
# Example 6: Feedback Loop
# ============================================================================

async def example_feedback_loop():
    """
    Submit feedback after executing translated query.

    Use case: Improving translation quality over time
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    # Step 1: Translate query
    cypher = """
    MATCH (u:User)-[:LOGGED_INTO]->(d:Device)
    WHERE d.os = "Windows"
    RETURN u.name, count(d) as device_count
    """

    context = {"schema_version": "1.2.0"}
    result = await client.translate(cypher, context)

    translation_id = result['translation_id']
    kql_query = result['kql_query']

    # Step 2: Execute KQL against Sentinel (pseudo-code)
    sentinel_client = None  # Your Sentinel client
    # execution_result = await sentinel_client.execute(kql_query)
    # For demonstration:
    execution_result = {
        "success": True,
        "execution_time_ms": 1250,
        "result_count": 45,
        "rows": [...]  # Actual results
    }

    # Step 3: Validate correctness (optional - could compare with Cypher execution)
    correctness = True  # Assume correct for this example

    # Step 4: Submit feedback
    await client.submit_feedback(
        translation_id=translation_id,
        rating=5,  # 1-5 scale
        correctness=correctness,
        actual_execution_time_ms=execution_result['execution_time_ms'],
        actual_result_count=execution_result['result_count'],
        comments="Translation worked well, performance was good"
    )

    print("Feedback submitted successfully!")
    print(f"  Translation ID: {translation_id}")
    print(f"  Rating: 5/5")
    print(f"  Execution time: {execution_result['execution_time_ms']}ms")


# ============================================================================
# Example 7: Error Handling
# ============================================================================

async def example_error_handling():
    """
    Demonstrate error handling for various failure scenarios.
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    # Scenario 1: Untranslatable pattern
    untranslatable_cypher = """
    MATCH path = (a)-[:REL*]->(b)
    WHERE length(path) > 10
    RETURN path
    """

    try:
        result = await client.translate(
            untranslatable_cypher,
            {"schema_version": "1.2.0"}
        )
    except Exception as e:
        print(f"Error: {e}")
        # Handle error - possibly show suggested alternative

    # Scenario 2: Low confidence
    complex_cypher = """
    MATCH (a)-[:R1*1..5]->(b)<-[:R2*1..3]-(c)
    WHERE a.id = "X"
    RETURN a, b, c
    """

    result = await client.translate(
        complex_cypher,
        {"schema_version": "1.2.0"},
        {"confidence_threshold": 0.9}  # High threshold
    )

    if result['status'] == 'partial':
        print("Warning: Low confidence translation")
        print(f"Confidence: {result['confidence']}")
        print("Consider reviewing or using alternative approach")

    # Scenario 3: Timeout
    very_complex_cypher = """
    MATCH path = (a)-[:REL1|:REL2|:REL3*1..10]->(b)
    WHERE ALL(n IN nodes(path) WHERE n.property = "value")
    RETURN path
    """

    try:
        result = await client.translate(
            very_complex_cypher,
            {"schema_version": "1.2.0"},
            {"async_mode": True}  # Use async for complex queries
        )

        # Poll with timeout
        max_wait = 30  # seconds
        waited = 0
        while result['status'] == 'processing' and waited < max_wait:
            await asyncio.sleep(1)
            waited += 1
            result = await client.get_translation_status(result['job_id'])

        if result['status'] != 'completed':
            print(f"Translation timed out or failed")
            # Handle timeout

    except Exception as e:
        print(f"Translation error: {e}")


# ============================================================================
# Example 8: Pattern Cache Exploration
# ============================================================================

async def example_pattern_cache():
    """
    Explore cached translation patterns.

    Use case: Understanding translation coverage or warming up cache
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    # Get all graph operator patterns with high confidence
    patterns = await client.get_pattern_cache(
        pattern_type="graph_operators",
        min_confidence=0.9,
        limit=50
    )

    print("High-Confidence Graph Operator Patterns:")
    print(f"Found {len(patterns['patterns'])} patterns\n")

    for pattern in patterns['patterns'][:10]:  # Show first 10
        print(f"Pattern ID: {pattern['pattern_id']}")
        print(f"  Confidence: {pattern['confidence']}")
        print(f"  Usage Count: {pattern['usage_count']}")
        print(f"  Success Rate: {pattern['success_rate'] * 100:.1f}%")
        print(f"  Avg Execution Time: {pattern['avg_execution_time_ms']}ms")
        print(f"  Cypher Template: {pattern['cypher_pattern'][:80]}...")
        print(f"  Tags: {', '.join(pattern['tags'])}")
        print()


# ============================================================================
# Example 9: Production Integration Pattern
# ============================================================================

async def example_production_integration():
    """
    Complete production integration pattern.

    Demonstrates:
    - Translation with fallback
    - Execution
    - Monitoring
    - Feedback
    """

    client = AgenticTranslatorClient(api_key="your_api_key")

    cypher = """
    MATCH (u:User)-[:OWNS]->(d:Device)-[:CONNECTS_TO]->(n:Network)
    WHERE u.department = "IT" AND n.security_zone = "DMZ"
    RETURN u.name, d.hostname, n.name
    """

    context = {
        "schema_version": "1.2.0",
        "performance_profile": "interactive"
    }

    # Step 1: Translate with retry and fallback
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            translation = await client.translate(cypher, context)

            if translation['confidence'] >= 0.8:
                break  # Acceptable confidence

            print(f"Low confidence ({translation['confidence']}), retrying...")

        except Exception as e:
            print(f"Translation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries:
                print("All translation attempts failed")
                return None

    # Step 2: Log translation metrics
    print(f"Translation succeeded:")
    print(f"  Confidence: {translation['confidence']}")
    print(f"  Strategy: {translation['strategy']}")
    print(f"  Time: {translation['metadata']['translation_time_ms']}ms")

    # Step 3: Execute KQL
    sentinel_client = None  # Your Sentinel client
    # execution_result = await sentinel_client.execute(translation['kql_query'])
    execution_result = {"execution_time_ms": 850, "result_count": 23}

    # Step 4: Compare estimated vs actual performance
    estimated_time = translation['estimated_performance']['execution_time_ms']
    actual_time = execution_result['execution_time_ms']
    performance_ratio = actual_time / estimated_time

    print(f"\nPerformance:")
    print(f"  Estimated: {estimated_time}ms")
    print(f"  Actual: {actual_time}ms")
    print(f"  Ratio: {performance_ratio:.2f}x")

    # Step 5: Submit feedback
    if performance_ratio < 1.5:  # Within acceptable range
        await client.submit_feedback(
            translation_id=translation['translation_id'],
            rating=5,
            correctness=True,
            actual_execution_time_ms=actual_time,
            actual_result_count=execution_result['result_count']
        )
    else:
        await client.submit_feedback(
            translation_id=translation['translation_id'],
            rating=3,
            correctness=True,
            actual_execution_time_ms=actual_time,
            issues=["Performance estimate was inaccurate"]
        )

    return execution_result


# ============================================================================
# Main Runner
# ============================================================================

async def main():
    """Run all examples."""

    print("=" * 80)
    print("Agentic AI Translation Layer - Example Usage")
    print("=" * 80)

    examples = [
        ("Basic Translation", example_basic_translation),
        ("Async Translation", example_async_translation),
        ("Batch Translation", example_batch_translation),
        ("Optimization", example_optimize_existing_kql),
        ("Semantic Validation", example_semantic_validation),
        ("Feedback Loop", example_feedback_loop),
        ("Error Handling", example_error_handling),
        ("Pattern Cache", example_pattern_cache),
        ("Production Integration", example_production_integration)
    ]

    for name, example_func in examples:
        print(f"\n{'=' * 80}")
        print(f"Example: {name}")
        print(f"{'=' * 80}\n")

        try:
            # Note: These would actually run if the client was implemented
            # For now, they demonstrate the API usage patterns
            # await example_func()
            print(f"[Example code shown above - would execute with real client]")
        except Exception as e:
            print(f"Error running example: {e}")

        print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    # asyncio.run(main())
    print("""
This file demonstrates example usage patterns for the Agentic AI Translation Layer API.

To use in practice:
1. Implement the AgenticTranslatorClient with actual HTTP calls
2. Replace placeholder Sentinel client with real implementation
3. Run individual examples or integrate into your application

Key patterns demonstrated:
- Basic and async translation
- Batch processing
- Query optimization
- Semantic validation
- Feedback loops for continuous learning
- Error handling and resilience
- Production integration
""")
