import pytest
from app import crud
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

@pytest.fixture
def mock_db_result():
    """Mock database result for testing"""
    result = MagicMock()
    result.mappings.return_value.first.return_value = {"id": 1, "name": "Test Item", "description": "Description", "price": 10.0}
    result.mappings.return_value.all.return_value = [
        {"id": 1, "name": "Item 1", "description": "Description 1", "price": 10.0},
        {"id": 2, "name": "Item 2", "description": "Description 2", "price": 20.0}
    ]
    result.mappings.return_value.one.return_value = {"id": 1, "name": "New Item", "description": "New Description", "price": 15.0}
    result.scalar_one_or_none.return_value = 1
    result.scalar_one.return_value = "Test Rule"
    result.scalars.return_value.all.return_value = ["Rule 1", "Rule 2"]
    result.fetchall.return_value = [
        type('obj', (object,), {'sender': 'user', 'message': 'Hello', 'timestamp': '2023-01-01 12:00:00'})(),
        type('obj', (object,), {'sender': 'bot', 'message': 'Hi there', 'timestamp': '2023-01-01 12:01:00'})()
    ]
    return result

@pytest.mark.asyncio
async def test_get_user(mock_async_session, mock_db_result):
    """Test get_user function"""
    # Configure mock session
    mock_async_session.execute.return_value = mock_db_result
    
    # Call the function
    user = await crud.get_user(mock_async_session, 1)
    
    # Assertions
    assert user is not None
    assert user['id'] == 1
    assert user['name'] == 'Test Item'
    mock_async_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_not_found(mock_async_session):
    """Test get_user function when user not found"""
    # Configure mock session to return None
    result = MagicMock()
    result.mappings.return_value.first.return_value = None
    mock_async_session.execute.return_value = result
    
    # Call the function
    user = await crud.get_user(mock_async_session, 999)
    
    # Assertions
    assert user is None
    mock_async_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_products(mock_async_session, mock_db_result):
    """Test get_products function"""
    # Configure mock session
    mock_async_session.execute.return_value = mock_db_result
    
    # Call the function
    products = await crud.get_products(mock_async_session, limit=10)
    
    # Assertions
    assert len(products) == 2
    assert products[0]['id'] == 1
    assert products[0]['name'] == 'Item 1'
    assert products[1]['id'] == 2
    mock_async_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_conversation_history_db(mock_async_session, mock_db_result):
    """Test get_conversation_history_db function"""
    # Configure mock session
    mock_async_session.execute.return_value = mock_db_result
    
    # Call the function
    history = await crud.get_conversation_history_db(mock_async_session, "test-conv-id")
    
    # Assertions
    assert len(history) == 2
    assert history[0]['role'] == 'user'
    assert history[0]['content'] == 'Hello'
    assert history[1]['role'] == 'assistant'
    assert history[1]['content'] == 'Hi there'
    mock_async_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_add_conversation_message(mock_async_session):
    """Test add_conversation_message function"""
    # Call the function
    await crud.add_conversation_message(
        mock_async_session, 1, "test-conv-id", "user", "Hello"
    )
    
    # Assertions
    mock_async_session.execute.assert_called_once()
    mock_async_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_product(mock_async_session, mock_db_result):
    """Test create_product function"""
    # Configure mock session
    mock_async_session.execute.return_value = mock_db_result
    
    # Call the function
    product = await crud.create_product(
        mock_async_session, "New Product", "Description", 25.99
    )
    
    # Assertions
    assert product is not None
    assert product['id'] == 1
    assert product['name'] == 'New Item'
    mock_async_session.execute.assert_called_once()
    mock_async_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_product(mock_async_session, mock_db_result):
    """Test update_product function"""
    # Configure mock session
    mock_async_session.execute.return_value = mock_db_result
    
    # Call the function
    product = await crud.update_product(
        mock_async_session, 1, "Updated Product", "Updated Description", 29.99
    )
    
    # Assertions
    assert product is not None
    assert product['id'] == 1
    assert product['name'] == 'Test Item'
    mock_async_session.execute.assert_called_once()
    mock_async_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_product(mock_async_session, mock_db_result):
    """Test delete_product function"""
    # Configure mock session
    mock_async_session.execute.return_value = mock_db_result
    
    # Call the function
    result = await crud.delete_product(mock_async_session, 1)
    
    # Assertions
    assert result is True
    mock_async_session.execute.assert_called_once()
    mock_async_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_product_not_found(mock_async_session):
    """Test delete_product function when product not found"""
    # Configure mock session to return None
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_async_session.execute.return_value = result
    
    # Call the function
    result = await crud.delete_product(mock_async_session, 999)
    
    # Assertions
    assert result is False
    mock_async_session.execute.assert_called_once()
    mock_async_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_db_error(mock_async_session):
    """Test handle_db_error function"""
    # Call the function with a mock error
    error = Exception("Test error")
    
    # Test that the function raises a DatabaseError
    with pytest.raises(crud.DatabaseError):
        await crud.handle_db_error(mock_async_session, error, "test_operation")
    
    # Assertions
    mock_async_session.rollback.assert_called_once() 