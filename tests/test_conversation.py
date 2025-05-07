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
    mock_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    
    with patch('app.crud.get_conversation_history_db', return_value=mock_history) as mock_get_history:
        conversation_id = "test-conversation-id"
        result_id, result_history = await get_conversation_history(mock_async_session, conversation_id)
        
        assert result_id == conversation_id
        assert result_history == mock_history
        mock_get_history.assert_called_once_with(mock_async_session, conversation_id)

@pytest.mark.asyncio
async def test_get_conversation_history_new(mock_async_session):
    """Test get_conversation_history with no conversation ID (new conversation)"""
    test_uuid = "test-uuid-123"
    with patch('uuid.uuid4', return_value=test_uuid):
        result_id, result_history = await get_conversation_history(mock_async_session, None)
        
        assert result_id == str(test_uuid)
        assert result_history == []

@pytest.mark.asyncio
async def test_get_conversation_history_db_error(mock_async_session):
    """Test get_conversation_history handling database errors gracefully"""
    db_error = DatabaseError("Test DB error")
    with patch('app.crud.get_conversation_history_db', side_effect=db_error) as mock_get_history:
        conversation_id = "test-conversation-id"
        result_id, result_history = await get_conversation_history(mock_async_session, conversation_id)
        
        assert result_id == conversation_id
        assert result_history == []
        mock_get_history.assert_called_once()
        
        mock_get_history.reset_mock()
        
        with patch('uuid.uuid4', return_value="test-uuid-456"):
            result_id, result_history = await get_conversation_history(mock_async_session, None)
            
            assert result_id == "test-uuid-456"
            assert result_history == []
            mock_get_history.assert_not_called()

@pytest.mark.asyncio
async def test_get_conversation_history_unexpected_error(mock_async_session):
    """Test get_conversation_history handling unexpected errors gracefully"""
    unexpected_error = Exception("Unexpected error")
    with patch('app.crud.get_conversation_history_db', side_effect=unexpected_error) as mock_get_history:
        with patch('uuid.uuid4', return_value="fallback-uuid-123"):
            conversation_id = "test-conversation-id"
            result_id, result_history = await get_conversation_history(mock_async_session, conversation_id)
            
            assert result_id == "fallback-uuid-123"
            assert result_history == []
            mock_get_history.assert_called_once()

@pytest.mark.asyncio
async def test_add_message_to_history_success(mock_async_session):
    """Test add_message_to_history function (successful case)"""
    with patch('app.crud.add_conversation_message') as mock_add_message:
        await add_message_to_history(
            mock_async_session, 
            user_id=1,
            conversation_id="test-conv-id",
            role="user",
            content="Hello"
        )
        
        mock_add_message.assert_called_once_with(
            mock_async_session, 1, "test-conv-id", "user", "Hello"
        )

@pytest.mark.asyncio
async def test_add_message_to_history_assistant_role(mock_async_session):
    """Test add_message_to_history function with assistant role"""
    with patch('app.crud.add_conversation_message') as mock_add_message:
        await add_message_to_history(
            mock_async_session, 
            user_id=1,
            conversation_id="test-conv-id",
            role="assistant",
            content="Hello user"
        )
        
        mock_add_message.assert_called_once_with(
            mock_async_session, 1, "test-conv-id", "bot", "Hello user"
        )

@pytest.mark.asyncio
async def test_add_message_to_history_db_error(mock_async_session):
    """Test add_message_to_history function handling database errors"""
    db_error = DatabaseError("Test DB error")
    with patch('app.crud.add_conversation_message', side_effect=db_error) as mock_add_message:
        with pytest.raises(DatabaseError):
            await add_message_to_history(
                mock_async_session, 
                user_id=1,
                conversation_id="test-conv-id",
                role="user",
                content="Hello"
            )
        
        mock_add_message.assert_called_once()

@pytest.mark.asyncio
async def test_add_message_to_history_unexpected_error(mock_async_session):
    """Test add_message_to_history function handling unexpected errors"""
    unexpected_error = Exception("Unexpected error")
    with patch('app.crud.add_conversation_message', side_effect=unexpected_error) as mock_add_message:
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