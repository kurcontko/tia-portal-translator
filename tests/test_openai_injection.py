"""Tests for OpenAI service client injection and tenacity retry logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from tia_portal_translator.services.openai_service import OpenAITranslationService


@pytest.mark.asyncio
async def test_openai_client_injection():
    """Test that we can inject a mock client for testing."""
    # Create mock client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Bonjour le monde"
    
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Create service with injected client
    service = OpenAITranslationService(
        source_language="en",
        target_language="fr",
        client=mock_client,
        model="gpt-4-test",
    )
    
    # Test translation
    result = await service.translate("Hello world")
    
    # Verify
    assert result == "Bonjour le monde"
    mock_client.chat.completions.create.assert_called_once()
    
    # Verify the call had correct parameters
    call_args = mock_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gpt-4-test"
    assert any("fr" in msg["content"] for msg in call_args.kwargs["messages"] if msg["role"] == "system")


@pytest.mark.asyncio
async def test_openai_custom_model():
    """Test that custom model parameter works."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test translation"
    
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Create service with custom model
    service = OpenAITranslationService(
        client=mock_client,
        model="custom-model-123",
    )
    
    await service.translate("test")
    
    # Verify custom model was used
    call_args = mock_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "custom-model-123"


@pytest.mark.asyncio
async def test_openai_empty_response_error():
    """Test that empty responses raise TranslationError."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None  # Empty response
    
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    service = OpenAITranslationService(client=mock_client)
    
    with pytest.raises(Exception) as exc_info:
        await service.translate("test")
    
    assert "empty response" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_openai_retry_on_failure():
    """Test that tenacity retries on failure."""
    mock_client = MagicMock()
    
    # First two calls fail, third succeeds
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("API Error 1"),
            Exception("API Error 2"),
            MagicMock(
                choices=[MagicMock(message=MagicMock(content="Success after retry"))]
            ),
        ]
    )
    
    service = OpenAITranslationService(client=mock_client)
    
    result = await service.translate("test")
    
    # Should succeed after retries
    assert result == "Success after retry"
    
    # Should have been called 3 times (2 failures + 1 success)
    assert mock_client.chat.completions.create.call_count == 3
