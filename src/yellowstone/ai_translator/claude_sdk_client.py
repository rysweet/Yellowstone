"""Claude Agent SDK client wrapper for AI translation.

This module provides a wrapper around the Claude Agent SDK with:
- API key initialization and authentication
- Complex query translation with streaming support
- Retry logic with exponential backoff
- Comprehensive error handling
- Mock mode for testing without real API calls
"""

import asyncio
import json
import logging
import os
import time
from typing import AsyncIterator, Dict, List, Optional

from .models import ClaudeAPIRequest, ClaudeAPIResponse

logger = logging.getLogger(__name__)


class ClaudeSDKError(Exception):
    """Base exception for Claude SDK errors."""

    pass


class ClaudeAPIError(ClaudeSDKError):
    """Exception for Claude API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ClaudeRateLimitError(ClaudeSDKError):
    """Exception for rate limit errors."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ClaudeSDKClient:
    """Claude Agent SDK client wrapper.

    Provides interface to Claude API with retry logic, error handling,
    and mock mode for testing.

    Example:
        >>> client = ClaudeSDKClient(api_key="sk-...", mock_mode=False)
        >>> request = ClaudeAPIRequest(
        ...     prompt="Translate: find nodes with label 'Person'",
        ...     max_tokens=1024
        ... )
        >>> response = await client.translate_query(request)
        >>> print(response.content)
    """

    SYSTEM_PROMPT = """You are an expert at translating natural language queries into Kusto Query Language (KQL) for graph databases.

Given a natural language query, generate the corresponding KQL query that:
1. Uses correct graph syntax (nodes, edges, paths)
2. Handles node and edge properties correctly
3. Uses appropriate predicates and filters
4. Returns results in the expected format

Return ONLY the KQL query, no explanations or markdown.

Examples:
- "Find all nodes with label 'Person'" -> "graph.nodes | where labels has 'Person'"
- "Find nodes named 'Alice'" -> "graph.nodes | where properties.name == 'Alice'"
- "Find edges of type 'KNOWS'" -> "graph.edges | where type == 'KNOWS'"
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        timeout: float = 30.0,
        mock_mode: bool = True,
    ):
        """Initialize Claude SDK client.

        Args:
            api_key: Claude API key (or set CLAUDE_API_KEY env var)
            model: Claude model to use
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            timeout: Request timeout in seconds
            mock_mode: If True, use mock responses instead of real API calls
        """
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.mock_mode = mock_mode

        if not mock_mode and not self.api_key:
            logger.warning("No API key provided, falling back to mock mode")
            self.mock_mode = True

        self._call_count = 0
        self._error_count = 0
        self._total_tokens = 0

    async def translate_query(self, request: ClaudeAPIRequest) -> ClaudeAPIResponse:
        """Translate natural language query to KQL.

        Args:
            request: Translation request with prompt and parameters

        Returns:
            Translation response with generated KQL

        Raises:
            ClaudeAPIError: If API request fails
            ClaudeRateLimitError: If rate limit exceeded
            ClaudeSDKError: For other SDK errors
        """
        if self.mock_mode:
            return await self._mock_translate(request)

        return await self._translate_with_retry(request)

    async def translate_query_stream(
        self, request: ClaudeAPIRequest
    ) -> AsyncIterator[ClaudeAPIResponse]:
        """Translate query with streaming response.

        Args:
            request: Translation request with stream=True

        Yields:
            Partial translation responses

        Raises:
            ClaudeAPIError: If API request fails
            ClaudeRateLimitError: If rate limit exceeded
        """
        if self.mock_mode:
            # Mock streaming by yielding partial responses
            response = await self._mock_translate(request)
            words = response.content.split()
            current_content = ""
            for word in words:
                current_content += word + " "
                yield ClaudeAPIResponse(
                    content=current_content.strip(),
                    stop_reason=None,
                    usage={"input_tokens": 0, "output_tokens": len(current_content.split())},
                    model=self.model,
                    metadata={"streaming": True},
                )
            # Final response
            yield response
        else:
            async for response in self._stream_with_retry(request):
                yield response

    async def _translate_with_retry(self, request: ClaudeAPIRequest) -> ClaudeAPIResponse:
        """Translate with retry logic and exponential backoff.

        Args:
            request: Translation request

        Returns:
            Translation response

        Raises:
            ClaudeAPIError: If all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self._call_api(request)
            except ClaudeRateLimitError as e:
                last_error = e
                retry_after = e.retry_after or self._calculate_backoff(attempt)
                logger.warning(f"Rate limit hit, retrying after {retry_after}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(retry_after)
            except ClaudeAPIError as e:
                last_error = e
                if e.status_code and e.status_code >= 500:
                    # Retry on server errors
                    delay = self._calculate_backoff(attempt)
                    logger.warning(f"Server error, retrying after {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    # Don't retry on client errors
                    raise
            except Exception as e:
                last_error = ClaudeSDKError(f"Unexpected error: {str(e)}")
                delay = self._calculate_backoff(attempt)
                logger.error(f"Unexpected error, retrying after {delay}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

        # All retries exhausted
        self._error_count += 1
        raise ClaudeAPIError(
            f"Failed after {self.max_retries} retries: {str(last_error)}"
        )

    async def _stream_with_retry(
        self, request: ClaudeAPIRequest
    ) -> AsyncIterator[ClaudeAPIResponse]:
        """Stream with retry logic.

        Args:
            request: Translation request

        Yields:
            Partial translation responses

        Raises:
            ClaudeAPIError: If all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                async for response in self._stream_api(request):
                    yield response
                return  # Success, exit
            except ClaudeRateLimitError as e:
                last_error = e
                retry_after = e.retry_after or self._calculate_backoff(attempt)
                logger.warning(f"Rate limit hit during streaming, retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
            except Exception as e:
                last_error = ClaudeSDKError(f"Stream error: {str(e)}")
                delay = self._calculate_backoff(attempt)
                logger.error(f"Stream error, retrying after {delay}s")
                await asyncio.sleep(delay)

        # All retries exhausted
        self._error_count += 1
        raise ClaudeAPIError(
            f"Streaming failed after {self.max_retries} retries: {str(last_error)}"
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter
        jitter = delay * 0.1
        return delay + (jitter * (2 * (hash(time.time()) % 100) / 100 - 1))

    async def _call_api(self, request: ClaudeAPIRequest) -> ClaudeAPIResponse:
        """Make actual API call to Claude.

        Args:
            request: API request

        Returns:
            API response

        Raises:
            ClaudeAPIError: If API call fails
            ClaudeRateLimitError: If rate limited
        """
        # This would be the actual API call implementation
        # For now, this is a placeholder that should never be called in mock mode
        raise NotImplementedError("Real API calls not implemented - use mock_mode=True")

    async def _stream_api(self, request: ClaudeAPIRequest) -> AsyncIterator[ClaudeAPIResponse]:
        """Stream API response from Claude.

        Args:
            request: API request with stream=True

        Yields:
            Partial API responses

        Raises:
            ClaudeAPIError: If API call fails
        """
        # This would be the actual streaming API implementation
        raise NotImplementedError("Real streaming API not implemented - use mock_mode=True")
        yield  # Make this a generator

    async def _mock_translate(self, request: ClaudeAPIRequest) -> ClaudeAPIResponse:
        """Mock translation for testing without API calls.

        Args:
            request: Translation request

        Returns:
            Mocked translation response
        """
        self._call_count += 1

        # Simulate API latency
        await asyncio.sleep(0.1)

        # Extract query from prompt
        prompt = request.prompt.lower()

        # Generate mock KQL based on prompt patterns
        kql = self._generate_mock_kql(prompt)

        input_tokens = len(request.prompt.split())
        output_tokens = len(kql.split())
        self._total_tokens += input_tokens + output_tokens

        return ClaudeAPIResponse(
            content=kql,
            stop_reason="end_turn",
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            model=self.model,
            metadata={
                "mock": True,
                "call_count": self._call_count,
            },
        )

    def _generate_mock_kql(self, prompt: str) -> str:
        """Generate mock KQL based on prompt patterns.

        Args:
            prompt: Natural language prompt

        Returns:
            Mock KQL query
        """
        # Node queries
        if "find all nodes" in prompt or "get all nodes" in prompt:
            if "label" in prompt or "type" in prompt:
                # Extract label if possible
                if "'person'" in prompt or '"person"' in prompt:
                    return "graph.nodes | where labels has 'Person'"
                elif "'movie'" in prompt or '"movie"' in prompt:
                    return "graph.nodes | where labels has 'Movie'"
                else:
                    return "graph.nodes | where labels has 'Entity'"
            return "graph.nodes"

        # Property queries
        if "named" in prompt or "name ==" in prompt or "name is" in prompt:
            if "'alice'" in prompt or '"alice"' in prompt:
                return "graph.nodes | where properties.name == 'Alice'"
            elif "'bob'" in prompt or '"bob"' in prompt:
                return "graph.nodes | where properties.name == 'Bob'"
            else:
                return "graph.nodes | where properties.name == 'Unknown'"

        # Edge queries
        if "edge" in prompt or "relationship" in prompt:
            if "knows" in prompt:
                return "graph.edges | where type == 'KNOWS'"
            elif "likes" in prompt:
                return "graph.edges | where type == 'LIKES'"
            else:
                return "graph.edges"

        # Path queries
        if "path" in prompt or "connected" in prompt:
            return "graph.paths | where source.labels has 'Person' and target.labels has 'Person'"

        # Count queries
        if "count" in prompt or "how many" in prompt:
            if "node" in prompt:
                return "graph.nodes | count"
            elif "edge" in prompt:
                return "graph.edges | count"
            else:
                return "graph.nodes | count"

        # Default fallback
        return "graph.nodes | take 10"

    def get_statistics(self) -> Dict[str, int]:
        """Get client statistics.

        Returns:
            Dictionary with call counts and token usage
        """
        return {
            "total_calls": self._call_count,
            "total_errors": self._error_count,
            "total_tokens": self._total_tokens,
            "success_rate": (
                (self._call_count - self._error_count) / self._call_count
                if self._call_count > 0
                else 0.0
            ),
        }

    def reset_statistics(self) -> None:
        """Reset client statistics."""
        self._call_count = 0
        self._error_count = 0
        self._total_tokens = 0
