import pytest
from app.conversation import get_conversation_history, add_message_to_history, Message
from app.crud import DatabaseError
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

@pytest.fixture
def mock_conversation_history():
    """Mock conversation history for testing"""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there, how can I help you?"}
    ]

@pytest.mark.asyncio
async def test_get_conversation_history_existing(mock_async_session):
    """Test get_conversation_history with an existing conversation ID"""
    # Define mock history to return
    mock_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    
    # Mock the crud.get_conversation_history_db function
    with patch('app.crud.get_conversation_history_db', return_value=mock_history) as mock_get_history:
        # Call the function
        conversation_id = "test-conversation-id"
        result_id, result_history = await get_conversation_history(mock_async_session, conversation_id)
        
        # Assertions
        assert result_id == conversation_id
        assert result_history == mock_history
        mock_get_history.assert_called_once_with(mock_async_session, conversation_id)

@pytest.mark.asyncio
async def test_get_conversation_history_new(mock_async_session):
    """Test get_conversation_history with no conversation ID (new conversation)"""
    # Mock uuid.uuid4 to return a predictable UUID
    test_uuid = "test-uuid-123"
    with patch('uuid.uuid4', return_value=test_uuid):
        # Call the function
        result_id, result_history = await get_conversation_history(mock_async_session, None)
        
        # Assertions
        assert result_id == str(test_uuid)
        assert result_history == []

@pytest.mark.asyncio
async def test_get_conversation_history_db_error(mock_async_session):
    """Test get_conversation_history handling database errors gracefully"""
    # Mock the crud function to raise a DatabaseError
    db_error = DatabaseError("Test DB error")
    with patch('app.crud.get_conversation_history_db', side_effect=db_error) as mock_get_history:
        # With existing conversation ID
        conversation_id = "test-conversation-id"
        result_id, result_history = await get_conversation_history(mock_async_session, conversation_id)
        
        # Should return same ID but empty history
        assert result_id == conversation_id
        assert result_history == []
        mock_get_history.assert_called_once()
        
        # Reset the mock
        mock_get_history.reset_mock()
        
        # With no conversation ID
        with patch('uuid.uuid4', return_value="test-uuid-456"):
            result_id, result_history = await get_conversation_history(mock_async_session, None)
            
            # Should return new ID and empty history
            assert result_id == "test-uuid-456"
            assert result_history == []
            mock_get_history.assert_not_called()

@pytest.mark.asyncio
async def test_get_conversation_history_unexpected_error(mock_async_session):
    """Test get_conversation_history handling unexpected errors gracefully"""
    # Mock the crud function to raise an unexpected error
    unexpected_error = Exception("Unexpected error")
    with patch('app.crud.get_conversation_history_db', side_effect=unexpected_error) as mock_get_history:
        # Call with a conversation ID
        with patch('uuid.uuid4', return_value="fallback-uuid-123"):
            conversation_id = "test-conversation-id"
            result_id, result_history = await get_conversation_history(mock_async_session, conversation_id)
            
            # Should return a fallback UUID and empty history
            assert result_id == "fallback-uuid-123"
            assert result_history == []
            mock_get_history.assert_called_once()

@pytest.mark.asyncio
async def test_add_message_to_history_success(mock_async_session):
    """Test add_message_to_history function (successful case)"""
    # Mock the crud.add_conversation_message function
    with patch('app.crud.add_conversation_message') as mock_add_message:
        # Call the function
        await add_message_to_history(
            mock_async_session, 
            user_id=1,
            conversation_id="test-conv-id",
            role="user",
            content="Hello"
        )
        
        # Assertions
        mock_add_message.assert_called_once_with(
            mock_async_session, 1, "test-conv-id", "user", "Hello"
        )

@pytest.mark.asyncio
async def test_add_message_to_history_assistant_role(mock_async_session):
    """Test add_message_to_history function with assistant role"""
    # Mock the crud.add_conversation_message function
    with patch('app.crud.add_conversation_message') as mock_add_message:
        # Call the function
        await add_message_to_history(
            mock_async_session, 
            user_id=1,
            conversation_id="test-conv-id",
            role="assistant",
            content="Hello user"
        )
        
        # Assertions (should map 'assistant' role to 'bot' sender)
        mock_add_message.assert_called_once_with(
            mock_async_session, 1, "test-conv-id", "bot", "Hello user"
        )

@pytest.mark.asyncio
async def test_add_message_to_history_db_error(mock_async_session):
    """Test add_message_to_history function handling database errors"""
    # Mock the crud function to raise a DatabaseError
    db_error = DatabaseError("Test DB error")
    with patch('app.crud.add_conversation_message', side_effect=db_error) as mock_add_message:
        # Call the function and expect the error to be propagated
        with pytest.raises(DatabaseError):
            await add_message_to_history(
                mock_async_session, 
                user_id=1,
                conversation_id="test-conv-id",
                role="user",
                content="Hello"
            )
        
        # Assertions
        mock_add_message.assert_called_once()

@pytest.mark.asyncio
async def test_add_message_to_history_unexpected_error(mock_async_session):
    """Test add_message_to_history function handling unexpected errors"""
    # Mock the crud function to raise an unexpected error
    unexpected_error = Exception("Unexpected error")
    with patch('app.crud.add_conversation_message', side_effect=unexpected_error) as mock_add_message:
        # Call the function and expect the error to be propagated
        with pytest.raises(Exception):
            await add_message_to_history(
                mock_async_session, 
                user_id=1,
                conversation_id="test-conv-id",
                role="user",
                content="Hello"
            )
        
        # Assertions
        mock_add_message.assert_called_once() 