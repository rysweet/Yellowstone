"""Claude Agent SDK client wrapper for AI translation.

This module provides a wrapper around the Claude Agent SDK with:
- API key initialization and authentication
- Complex query translation with streaming support
- Retry logic with exponential backoff
- Comprehensive error handling
"""

import asyncio
import json
import logging
import os
import time
from typing import AsyncIterator, Dict, List, Optional

from anthropic import AsyncAnthropic, APIError, RateLimitError, AuthenticationError, APIConnectionError

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

    Provides interface to Claude API with retry logic and error handling.

    Example:
        >>> client = ClaudeSDKClient(api_key="sk-...")
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
    ):
        """Initialize Claude SDK client.

        Args:
            api_key: Claude API key (or set CLAUDE_API_KEY env var)
            model: Claude model to use
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            timeout: Request timeout in seconds

        Raises:
            ValueError: If no API key provided
        """
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "CLAUDE_API_KEY required. Set environment variable or pass api_key parameter. "
                "Get API key from: https://console.anthropic.com"
            )

        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout

        # Initialize Anthropic client
        self._client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)

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
        if not self._client:
            raise ClaudeSDKError("Client not initialized - check API key")

        try:
            # Use system prompt from request or default
            system_prompt = request.system or self.SYSTEM_PROMPT

            # Make API call
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": request.prompt}],
                temperature=request.temperature,
            )

            # Update statistics
            self._call_count += 1
            self._total_tokens += message.usage.input_tokens + message.usage.output_tokens

            # Extract text content from response
            content = ""
            if message.content:
                # Handle both single content blocks and lists
                if isinstance(message.content, list):
                    content = "".join(
                        block.text for block in message.content
                        if hasattr(block, 'text')
                    )
                else:
                    content = message.content

            return ClaudeAPIResponse(
                content=content,
                stop_reason=message.stop_reason,
                usage={
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                model=message.model,
                metadata={"call_count": self._call_count},
            )

        except RateLimitError as e:
            # Extract retry-after header if available
            retry_after = None
            if hasattr(e, 'response') and e.response:
                retry_after = e.response.headers.get('retry-after')
                if retry_after:
                    try:
                        retry_after = float(retry_after)
                    except (ValueError, TypeError):
                        retry_after = None

            logger.warning(f"Rate limit error: {str(e)}")
            raise ClaudeRateLimitError(
                f"Rate limit exceeded: {str(e)}",
                retry_after=retry_after
            )

        except AuthenticationError as e:
            logger.error(f"Authentication error: {str(e)}")
            raise ClaudeAPIError(
                f"Authentication failed - check API key: {str(e)}",
                status_code=401
            )

        except APIConnectionError as e:
            logger.error(f"Network connection error: {str(e)}")
            raise ClaudeAPIError(
                f"Network connection failed: {str(e)}",
                status_code=None
            )

        except APIError as e:
            # Handle other API errors
            status_code = None
            if hasattr(e, 'status_code'):
                status_code = e.status_code

            logger.error(f"API error: {str(e)} (status: {status_code})")
            raise ClaudeAPIError(
                f"API error: {str(e)}",
                status_code=status_code
            )

        except Exception as e:
            logger.error(f"Unexpected error in API call: {str(e)}")
            raise ClaudeSDKError(f"Unexpected error: {str(e)}")

    async def _stream_api(self, request: ClaudeAPIRequest) -> AsyncIterator[ClaudeAPIResponse]:
        """Stream API response from Claude.

        Args:
            request: API request with stream=True

        Yields:
            Partial API responses

        Raises:
            ClaudeAPIError: If API call fails
        """
        if not self._client:
            raise ClaudeSDKError("Client not initialized - check API key")

        try:
            # Use system prompt from request or default
            system_prompt = request.system or self.SYSTEM_PROMPT

            # Track tokens for final response
            input_tokens = 0
            output_tokens = 0
            accumulated_content = ""

            # Stream API call
            async with self._client.messages.stream(
                model=self.model,
                max_tokens=request.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": request.prompt}],
                temperature=request.temperature,
            ) as stream:
                # Yield partial responses as text arrives
                async for text in stream.text_stream:
                    accumulated_content += text
                    yield ClaudeAPIResponse(
                        content=accumulated_content,
                        stop_reason=None,  # Not finished yet
                        usage={"input_tokens": 0, "output_tokens": 0},  # Will be updated in final
                        model=self.model,
                        metadata={"streaming": True, "partial": True},
                    )

                # Get final message with complete usage info
                final_message = await stream.get_final_message()

                # Update statistics
                self._call_count += 1
                self._total_tokens += final_message.usage.input_tokens + final_message.usage.output_tokens

                # Yield final complete response
                yield ClaudeAPIResponse(
                    content=accumulated_content,
                    stop_reason=final_message.stop_reason,
                    usage={
                        "input_tokens": final_message.usage.input_tokens,
                        "output_tokens": final_message.usage.output_tokens,
                    },
                    model=final_message.model,
                    metadata={"streaming": True, "partial": False, "call_count": self._call_count},
                )

        except RateLimitError as e:
            # Extract retry-after header if available
            retry_after = None
            if hasattr(e, 'response') and e.response:
                retry_after = e.response.headers.get('retry-after')
                if retry_after:
                    try:
                        retry_after = float(retry_after)
                    except (ValueError, TypeError):
                        retry_after = None

            logger.warning(f"Rate limit error during streaming: {str(e)}")
            raise ClaudeRateLimitError(
                f"Rate limit exceeded: {str(e)}",
                retry_after=retry_after
            )

        except AuthenticationError as e:
            logger.error(f"Authentication error during streaming: {str(e)}")
            raise ClaudeAPIError(
                f"Authentication failed - check API key: {str(e)}",
                status_code=401
            )

        except APIConnectionError as e:
            logger.error(f"Network connection error during streaming: {str(e)}")
            raise ClaudeAPIError(
                f"Network connection failed: {str(e)}",
                status_code=None
            )

        except APIError as e:
            # Handle other API errors
            status_code = None
            if hasattr(e, 'status_code'):
                status_code = e.status_code

            logger.error(f"API error during streaming: {str(e)} (status: {status_code})")
            raise ClaudeAPIError(
                f"API error: {str(e)}",
                status_code=status_code
            )

        except Exception as e:
            logger.error(f"Unexpected error during streaming: {str(e)}")
            raise ClaudeSDKError(f"Unexpected error: {str(e)}")

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
