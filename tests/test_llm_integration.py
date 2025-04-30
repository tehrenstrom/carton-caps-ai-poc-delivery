# For this Proof-of-Concept, 
# mocks are used for efficiency. Production testing might
# also include integration tests using sample data in a test database
# and potentially controlled tests against a live LLM endpoint 
# to validate prompt effectiveness and real data integration.

import pytest
from unittest.mock import patch, MagicMock
from app.llm_integration import generate_response
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def mock_model():
    with patch('app.llm_integration.model') as mock_model:
        yield mock_model

@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "school_name": "Test School"
    }

@pytest.fixture
def mock_products():
    return [
        {"id": 1, "name": "Product 1", "description": "Description 1", "price": 10.99},
        {"id": 2, "name": "Product 2", "description": "Description 2", "price": 20.99}
    ]

@pytest.fixture
def mock_faqs():
    return [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"}
    ]

@pytest.fixture
def mock_rules():
    return ["Rule 1", "Rule 2"]

def test_generate_response_happy_path(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test successful response generation"""
    mock_response = MagicMock()
    mock_response.text = "Hi there! Let me help you find what you need."
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    user_message = "Hello"
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]
    
    # Pass the required parameters directly (products, faqs, rules)
    response = generate_response(
        user_info=mock_user,
        history=conversation_history, 
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    assert "Hi" in response or "Hello" in response
    mock_model.start_chat.assert_called_once()
    mock_chat.send_message.assert_called_once_with(user_message)

def test_generate_response_error_handling(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test error handling in response generation"""
    # Override the mock_model fixture with None to simulate configuration failure
    with patch('app.llm_integration.model', None):
        user_message = "Hello"
        conversation_history = []
        
        # Pass the required parameters directly (products, faqs, rules)
        response = generate_response(
            user_info=mock_user,
            history=conversation_history, 
            user_message=user_message,
            products=mock_products,
            faqs=mock_faqs,
            rules=mock_rules
        )
        
        assert "Error: AI Service not configured correctly" in response 