"""Comprehensive test suite for Claude SDK client.

Tests cover:
- Mock mode functionality
- Real API integration (with proper mocking)
- Error handling (rate limits, auth, network)
- Retry logic
- Streaming support
- Statistics tracking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from anthropic import RateLimitError, AuthenticationError, APIConnectionError, APIError

from yellowstone.ai_translator.claude_sdk_client import (
    ClaudeSDKClient,
    ClaudeSDKError,
    ClaudeAPIError,
    ClaudeRateLimitError,
)
from yellowstone.ai_translator.models import ClaudeAPIRequest, ClaudeAPIResponse


class TestClaudeSDKClientMockMode:
    """Test suite for mock mode functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create client in mock mode."""
        return ClaudeSDKClient(mock_mode=True)

    @pytest.mark.asyncio
    async def test_mock_mode_initialization(self, mock_client):
        """Test mock mode initializes without API key."""
        assert mock_client.mock_mode is True
        assert mock_client._client is None
        assert mock_client._call_count == 0

    @pytest.mark.asyncio
    async def test_mock_translate_simple_query(self, mock_client):
        """Test mock translation of simple query."""
        request = ClaudeAPIRequest(
            prompt="Find all nodes with label 'Person'",
            max_tokens=1024,
        )
        response = await mock_client.translate_query(request)

        assert response.content is not None
        assert len(response.content) > 0
        assert "graph.nodes" in response.content or "Person" in response.content
        assert response.model == mock_client.model
        assert response.metadata.get("mock") is True

    @pytest.mark.asyncio
    async def test_mock_translate_edge_query(self, mock_client):
        """Test mock translation of edge query."""
        request = ClaudeAPIRequest(
            prompt="Find edges of type 'KNOWS'",
            max_tokens=1024,
        )
        response = await mock_client.translate_query(request)

        assert "graph.edges" in response.content or "KNOWS" in response.content

    @pytest.mark.asyncio
    async def test_mock_translate_count_query(self, mock_client):
        """Test mock translation of count query."""
        request = ClaudeAPIRequest(
            prompt="Count all nodes",
            max_tokens=1024,
        )
        response = await mock_client.translate_query(request)

        assert "count" in response.content.lower()

    @pytest.mark.asyncio
    async def test_mock_streaming(self, mock_client):
        """Test mock streaming functionality."""
        request = ClaudeAPIRequest(
            prompt="Find all nodes",
            max_tokens=1024,
            stream=True,
        )

        responses = []
        async for response in mock_client.translate_query_stream(request):
            responses.append(response)

        assert len(responses) > 0
        # Final response should have complete content
        assert responses[-1].content is not None
        assert len(responses[-1].content) > 0

    @pytest.mark.asyncio
    async def test_mock_statistics_tracking(self, mock_client):
        """Test statistics tracking in mock mode."""
        request = ClaudeAPIRequest(prompt="Find all nodes", max_tokens=1024)

        await mock_client.translate_query(request)
        await mock_client.translate_query(request)

        stats = mock_client.get_statistics()
        assert stats["total_calls"] == 2
        assert stats["total_errors"] == 0
        assert stats["total_tokens"] > 0
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_mock_reset_statistics(self, mock_client):
        """Test resetting statistics."""
        request = ClaudeAPIRequest(prompt="Find all nodes", max_tokens=1024)
        await mock_client.translate_query(request)

        mock_client.reset_statistics()
        stats = mock_client.get_statistics()

        assert stats["total_calls"] == 0
        assert stats["total_tokens"] == 0


class TestClaudeSDKClientRealAPI:
    """Test suite for real API integration (with mocked Anthropic SDK)."""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a mock Anthropic API response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="graph.nodes | where labels has 'Person'")]
        mock_response.stop_reason = "end_turn"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=15)
        return mock_response

    @pytest.fixture
    def real_client(self):
        """Create client in real mode with fake API key."""
        return ClaudeSDKClient(api_key="sk-test-fake-key-123", mock_mode=False)

    @pytest.mark.asyncio
    async def test_real_mode_initialization(self, real_client):
        """Test real mode initializes with API key."""
        assert real_client.mock_mode is False
        assert real_client._client is not None
        assert real_client.api_key == "sk-test-fake-key-123"

    @pytest.mark.asyncio
    async def test_no_api_key_falls_back_to_mock(self):
        """Test client falls back to mock mode without API key."""
        client = ClaudeSDKClient(api_key=None, mock_mode=False)
        assert client.mock_mode is True

    @pytest.mark.asyncio
    async def test_real_api_call_success(self, real_client, mock_anthropic_response):
        """Test successful real API call."""
        request = ClaudeAPIRequest(
            prompt="Find nodes with label 'Person'",
            max_tokens=1024,
        )

        # Mock the Anthropic client
        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            return_value=mock_anthropic_response
        ):
            response = await real_client.translate_query(request)

            assert response.content == "graph.nodes | where labels has 'Person'"
            assert response.stop_reason == "end_turn"
            assert response.usage["input_tokens"] == 10
            assert response.usage["output_tokens"] == 15
            assert response.model == "claude-3-5-sonnet-20241022"

    @pytest.mark.asyncio
    async def test_real_api_call_with_custom_system_prompt(self, real_client, mock_anthropic_response):
        """Test API call with custom system prompt."""
        custom_prompt = "You are a specialized KQL translator."
        request = ClaudeAPIRequest(
            prompt="Find nodes",
            max_tokens=1024,
            system=custom_prompt,
        )

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            return_value=mock_anthropic_response
        ) as mock_create:
            response = await real_client.translate_query(request)

            # Verify custom system prompt was used
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['system'] == custom_prompt

    @pytest.mark.asyncio
    async def test_real_api_streaming_success(self, real_client):
        """Test successful streaming API call."""
        request = ClaudeAPIRequest(
            prompt="Find nodes",
            max_tokens=1024,
            stream=True,
        )

        # Mock streaming response
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        async def text_stream_generator():
            yield "graph."
            yield "nodes"

        mock_stream.text_stream = text_stream_generator()

        mock_final_message = MagicMock()
        mock_final_message.stop_reason = "end_turn"
        mock_final_message.model = "claude-3-5-sonnet-20241022"
        mock_final_message.usage = MagicMock(input_tokens=10, output_tokens=15)
        mock_stream.get_final_message = AsyncMock(return_value=mock_final_message)

        with patch.object(
            real_client._client.messages,
            'stream',
            return_value=mock_stream
        ):
            responses = []
            async for response in real_client.translate_query_stream(request):
                responses.append(response)

            assert len(responses) > 0
            # Final response should have complete content
            final = responses[-1]
            assert "graph.nodes" in final.content
            assert final.stop_reason == "end_turn"
            assert final.usage["input_tokens"] == 10
            assert final.usage["output_tokens"] == 15


class TestClaudeSDKClientErrorHandling:
    """Test suite for error handling."""

    @pytest.fixture
    def real_client(self):
        """Create client in real mode."""
        return ClaudeSDKClient(api_key="sk-test-fake-key-123", mock_mode=False)

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, real_client):
        """Test rate limit error is properly handled."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock rate limit error
        mock_error = RateLimitError("Rate limit exceeded", body=None, response=None)

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=mock_error
        ):
            with pytest.raises(ClaudeRateLimitError) as exc_info:
                await real_client.translate_query(request)

            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, real_client):
        """Test authentication error is properly handled."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock authentication error
        mock_error = AuthenticationError("Invalid API key", body=None, response=None)

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=mock_error
        ):
            with pytest.raises(ClaudeAPIError) as exc_info:
                await real_client.translate_query(request)

            assert "Authentication failed" in str(exc_info.value)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, real_client):
        """Test network connection error is properly handled."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock connection error
        mock_error = APIConnectionError("Connection failed", request=None)

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=mock_error
        ):
            with pytest.raises(ClaudeAPIError) as exc_info:
                await real_client.translate_query(request)

            assert "Network connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generic_api_error_handling(self, real_client):
        """Test generic API error is properly handled."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock generic API error
        mock_error = APIError("Something went wrong", body=None, response=None)

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=mock_error
        ):
            with pytest.raises(ClaudeAPIError) as exc_info:
                await real_client.translate_query(request)

            assert "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, real_client):
        """Test unexpected error is properly handled."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock unexpected error
        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected error")
        ):
            with pytest.raises(ClaudeSDKError) as exc_info:
                await real_client.translate_query(request)

            assert "Unexpected error" in str(exc_info.value)


class TestClaudeSDKClientRetryLogic:
    """Test suite for retry logic."""

    @pytest.fixture
    def real_client(self):
        """Create client with retry configuration."""
        return ClaudeSDKClient(
            api_key="sk-test-fake-key-123",
            mock_mode=False,
            max_retries=3,
            base_delay=0.1,
        )

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, real_client):
        """Test retry logic on rate limit error."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock response that succeeds on second try
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="graph.nodes")]
        mock_response.stop_reason = "end_turn"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=15)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit", body=None, response=None)
            return mock_response

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=side_effect
        ):
            response = await real_client.translate_query(request)

            assert response.content == "graph.nodes"
            assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, real_client):
        """Test retry logic on server error."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Mock response that succeeds on second try
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="graph.nodes")]
        mock_response.stop_reason = "end_turn"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=15)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                error = APIError("Server error", body=None, response=None)
                error.status_code = 500
                raise error
            return mock_response

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=side_effect
        ):
            response = await real_client.translate_query(request)

            assert response.content == "graph.nodes"
            assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, real_client):
        """Test no retry on client error (4xx)."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            error = APIError("Bad request", body=None, response=None)
            error.status_code = 400
            raise error

        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=side_effect
        ):
            with pytest.raises(ClaudeAPIError):
                await real_client.translate_query(request)

            assert call_count == 1  # Should not retry on client errors

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, real_client):
        """Test behavior when max retries are exhausted."""
        request = ClaudeAPIRequest(prompt="Find nodes", max_tokens=1024)

        # Always fail
        with patch.object(
            real_client._client.messages,
            'create',
            new_callable=AsyncMock,
            side_effect=RateLimitError("Rate limit", body=None, response=None)
        ):
            with pytest.raises(ClaudeAPIError) as exc_info:
                await real_client.translate_query(request)

            assert "Failed after" in str(exc_info.value)
            assert str(real_client.max_retries) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self, real_client):
        """Test exponential backoff calculation."""
        # Test backoff increases exponentially
        delay_0 = real_client._calculate_backoff(0)
        delay_1 = real_client._calculate_backoff(1)
        delay_2 = real_client._calculate_backoff(2)

        # Should roughly double each time (accounting for jitter)
        assert delay_1 > delay_0
        assert delay_2 > delay_1

        # Should not exceed max delay
        delay_100 = real_client._calculate_backoff(100)
        assert delay_100 <= real_client.max_delay * 1.1  # Allow for jitter


class TestClaudeSDKClientIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_full_workflow_mock_mode(self):
        """Test complete workflow in mock mode."""
        client = ClaudeSDKClient(mock_mode=True)

        # Create request
        request = ClaudeAPIRequest(
            prompt="Find all nodes with label 'Person' and age > 18",
            max_tokens=1024,
            temperature=0.0,
        )

        # Translate query
        response = await client.translate_query(request)

        # Verify response
        assert response.content is not None
        assert len(response.content) > 0
        assert response.usage["input_tokens"] > 0
        assert response.usage["output_tokens"] > 0

        # Check statistics
        stats = client.get_statistics()
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_full_workflow_real_mode(self):
        """Test complete workflow in real mode (mocked SDK)."""
        client = ClaudeSDKClient(api_key="sk-test-key", mock_mode=False)

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="graph.nodes | where labels has 'Person' and properties.age > 18")]
        mock_response.stop_reason = "end_turn"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.usage = MagicMock(input_tokens=20, output_tokens=25)

        with patch.object(
            client._client.messages,
            'create',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            request = ClaudeAPIRequest(
                prompt="Find all nodes with label 'Person' and age > 18",
                max_tokens=1024,
            )

            response = await client.translate_query(request)

            assert "graph.nodes" in response.content
            assert "Person" in response.content
            assert "age" in response.content

            stats = client.get_statistics()
            assert stats["total_calls"] == 1

    @pytest.mark.asyncio
    async def test_multiple_queries_statistics(self):
        """Test statistics across multiple queries."""
        client = ClaudeSDKClient(mock_mode=True)

        queries = [
            "Find all nodes",
            "Find all edges",
            "Count nodes",
            "Find paths",
        ]

        for query in queries:
            request = ClaudeAPIRequest(prompt=query, max_tokens=1024)
            await client.translate_query(request)

        stats = client.get_statistics()
        assert stats["total_calls"] == len(queries)
        assert stats["total_tokens"] > 0
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_streaming_integration(self):
        """Test streaming integration."""
        client = ClaudeSDKClient(mock_mode=True)

        request = ClaudeAPIRequest(
            prompt="Find all nodes with complex filtering",
            max_tokens=1024,
            stream=True,
        )

        partial_responses = []
        final_content = ""

        async for response in client.translate_query_stream(request):
            partial_responses.append(response)
            final_content = response.content

        assert len(partial_responses) > 0
        assert len(final_content) > 0
        assert final_content == partial_responses[-1].content
