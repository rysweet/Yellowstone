"""Example usage of Claude SDK client with real API integration.

This demonstrates:
- Real API calls (requires CLAUDE_API_KEY environment variable)
- Mock mode for testing without API key
- Streaming responses
- Error handling
- Statistics tracking
"""

import asyncio
import os
from yellowstone.ai_translator.claude_sdk_client import (
    ClaudeSDKClient,
    ClaudeAPIError,
    ClaudeRateLimitError,
)
from yellowstone.ai_translator.models import ClaudeAPIRequest


async def example_mock_mode():
    """Example using mock mode (no API key required)."""
    print("\n=== Example 1: Mock Mode ===")

    # Create client in mock mode
    client = ClaudeSDKClient(mock_mode=True)
    print(f"Client initialized in mock mode: {client.mock_mode}")

    # Create translation request
    request = ClaudeAPIRequest(
        prompt="Find all nodes with label 'Person' and age greater than 18",
        max_tokens=1024,
        temperature=0.0,
    )

    # Translate query
    response = await client.translate_query(request)
    print(f"Query: {request.prompt}")
    print(f"KQL: {response.content}")
    print(f"Tokens: {response.usage['input_tokens']} in, {response.usage['output_tokens']} out")

    # Get statistics
    stats = client.get_statistics()
    print(f"Statistics: {stats}")


async def example_real_mode():
    """Example using real API mode (requires API key)."""
    print("\n=== Example 2: Real API Mode ===")

    # Check if API key is available
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("CLAUDE_API_KEY not set - skipping real API example")
        print("Set CLAUDE_API_KEY environment variable to run this example")
        return

    # Create client with real API
    client = ClaudeSDKClient(api_key=api_key, mock_mode=False)
    print(f"Client initialized with real API")

    # Create translation request
    request = ClaudeAPIRequest(
        prompt="Find all Person nodes that have an outgoing KNOWS relationship",
        max_tokens=1024,
        temperature=0.0,
    )

    try:
        # Translate query
        response = await client.translate_query(request)
        print(f"Query: {request.prompt}")
        print(f"KQL: {response.content}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.usage['input_tokens']} in, {response.usage['output_tokens']} out")

        # Get statistics
        stats = client.get_statistics()
        print(f"Statistics: {stats}")

    except ClaudeRateLimitError as e:
        print(f"Rate limit error: {e}")
        if e.retry_after:
            print(f"Retry after: {e.retry_after} seconds")
    except ClaudeAPIError as e:
        print(f"API error: {e}")
        if e.status_code:
            print(f"Status code: {e.status_code}")


async def example_streaming():
    """Example using streaming mode."""
    print("\n=== Example 3: Streaming Mode ===")

    # Create client (using mock mode for demo)
    client = ClaudeSDKClient(mock_mode=True)

    # Create streaming request
    request = ClaudeAPIRequest(
        prompt="Find the shortest path between two Person nodes named 'Alice' and 'Bob'",
        max_tokens=1024,
        stream=True,
    )

    print(f"Query: {request.prompt}")
    print("Streaming response:")

    # Stream the response
    async for response in client.translate_query_stream(request):
        # Print each partial update (in real scenario, this would show incremental updates)
        is_final = not response.metadata.get("streaming") or not response.metadata.get("partial", True)
        if is_final:
            print(f"\nFinal KQL: {response.content}")
            print(f"Stop reason: {response.stop_reason}")
            break


async def example_error_handling():
    """Example demonstrating error handling."""
    print("\n=== Example 4: Error Handling ===")

    # Create client with invalid API key to demonstrate error handling
    client = ClaudeSDKClient(api_key="sk-invalid-key", mock_mode=False, max_retries=2)

    request = ClaudeAPIRequest(
        prompt="Find all nodes",
        max_tokens=1024,
    )

    try:
        response = await client.translate_query(request)
        print(f"Success: {response.content}")
    except ClaudeAPIError as e:
        print(f"Caught API error (expected with invalid key): {type(e).__name__}")
        print(f"Error message: {e}")
        if hasattr(e, 'status_code') and e.status_code:
            print(f"Status code: {e.status_code}")
    except Exception as e:
        print(f"Caught unexpected error: {type(e).__name__}: {e}")


async def example_multiple_queries():
    """Example with multiple queries and statistics."""
    print("\n=== Example 5: Multiple Queries ===")

    client = ClaudeSDKClient(mock_mode=True)

    queries = [
        "Find all Person nodes",
        "Find all KNOWS relationships",
        "Count total nodes in the graph",
        "Find paths between connected nodes",
    ]

    for i, query in enumerate(queries, 1):
        request = ClaudeAPIRequest(prompt=query, max_tokens=1024)
        response = await client.translate_query(request)
        print(f"{i}. Query: {query}")
        print(f"   KQL: {response.content}")

    # Show aggregate statistics
    stats = client.get_statistics()
    print(f"\nAggregate Statistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Total errors: {stats['total_errors']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")


async def example_custom_system_prompt():
    """Example using custom system prompt."""
    print("\n=== Example 6: Custom System Prompt ===")

    client = ClaudeSDKClient(mock_mode=True)

    # Custom system prompt for specialized translation
    custom_system = """You are a specialized KQL translator for security graph databases.
Focus on threat detection patterns and security relationships.
Use strict security-focused naming conventions."""

    request = ClaudeAPIRequest(
        prompt="Find all suspicious login attempts",
        max_tokens=1024,
        system=custom_system,
        temperature=0.0,
    )

    response = await client.translate_query(request)
    print(f"Query: {request.prompt}")
    print(f"KQL (with custom prompt): {response.content}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Claude SDK Client Examples")
    print("=" * 60)

    # Run examples
    await example_mock_mode()
    await example_real_mode()
    await example_streaming()
    await example_error_handling()
    await example_multiple_queries()
    await example_custom_system_prompt()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
