# For this Proof-of-Concept, 
# mocks are used for efficiency. Production testing might
# also include integration tests using sample data in a test database
# and potentially controlled tests against a live LLM endpoint 
# to validate prompt effectiveness and real data integration.

import pytest
from unittest.mock import patch, MagicMock
from app.llm_integration import generate_response
from app.crud import get_user, get_products, get_referral_faqs, get_referral_rules
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
    
    with patch('app.crud.get_user', return_value=mock_user), \
         patch('app.crud.get_products', return_value=mock_products), \
         patch('app.crud.get_referral_faqs', return_value=mock_faqs), \
         patch('app.crud.get_referral_rules', return_value=mock_rules):
        
        user_id = 1
        message = "Hello"
        conversation_history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"}
        ]
        
        response = generate_response(user_id, conversation_history, message)
        

        assert "Hi" in response or "Hello" in response
        mock_model.start_chat.assert_called_once()
        mock_chat.send_message.assert_called_once_with(message)

def test_generate_response_error_handling(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test error handling in response generation"""
    mock_model = None
    
    with patch('app.crud.get_user', return_value=mock_user), \
         patch('app.crud.get_products', return_value=mock_products), \
         patch('app.crud.get_referral_faqs', return_value=mock_faqs), \
         patch('app.crud.get_referral_rules', return_value=mock_rules), \
         patch('app.llm_integration.model', mock_model):
        
        user_id = 1
        message = "Hello"
        conversation_history = []
        
        response = generate_response(user_id, conversation_history, message)
        
        assert "Error: AI Service not configured correctly" in response 