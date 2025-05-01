# For this Proof-of-Concept, 
# mocks are used for efficiency. Production testing might
# also include integration tests using sample data in a test database
# and potentially controlled tests against a live LLM endpoint 
# to validate prompt effectiveness and real data integration.

import pytest
from unittest.mock import patch, MagicMock
from app.llm_integration import generate_response, truncate_history_by_tokens
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

def test_generate_response_error_handling(mock_user, mock_products, mock_faqs, mock_rules):
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

def test_generate_response_with_excessive_history(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test handling of excessive conversation history using token-aware truncation"""
    mock_response = MagicMock()
    mock_response.text = "Processed truncated history"
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    # Create a long conversation history
    long_history = []
    for i in range(20):  # Create 20 messages
        role = "user" if i % 2 == 0 else "assistant"
        long_history.append({
            "role": role,
            "content": f"This is message {i+1} with some additional text to increase token count"
        })
    
    user_message = "This is a test with long history"
    
    # Mock the truncate_history_by_tokens function to verify it's called
    truncated_history = long_history[-5:]  # Simulate keeping last 5 messages
    with patch('app.llm_integration.truncate_history_by_tokens', 
               return_value=(truncated_history, 1000)) as mock_truncate:
        
        # Call function with excessive history
        response = generate_response(
            user_info=mock_user,
            history=long_history,
            user_message=user_message,
            products=mock_products,
            faqs=mock_faqs,
            rules=mock_rules
        )
        
        # Verify response
        assert response == "Processed truncated history"
        
        # Verify token-aware truncation was called
        mock_truncate.assert_called_once()
        
        # Verify that the truncated history was used
        assert len(mock_model.start_chat.call_args[1]['history']) > 2  # System prompt + model response + truncated history
        
        # Check that we sent the user message to the model
        mock_chat.send_message.assert_called_once_with(user_message)

def test_generate_response_api_exception(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test handling of API exceptions"""
    # Set up mock to raise an exception when called
    mock_model.start_chat.side_effect = Exception("API Error")
    
    user_message = "Hello"
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]
    
    # Call function
    response = generate_response(
        user_info=mock_user,
        history=conversation_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Verify response contains the new error message
    assert "trouble generating a response" in response
    assert "support@cartoncaps.com" in response

def test_generate_response_empty_api_response(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test handling of empty API response"""
    mock_response = MagicMock()
    mock_response.text = ""  # Empty response
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    user_message = "Hello"
    conversation_history = [{"role": "user", "content": "Hi"}]
    
    # Call function
    response = generate_response(
        user_info=mock_user,
        history=conversation_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Verify response contains error message
    assert "Sorry, I received an empty response" in response
    mock_model.start_chat.assert_called_once()
    mock_chat.send_message.assert_called_once_with(user_message)

def test_generate_response_invalid_message_content(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test handling of invalid message content in history"""
    mock_response = MagicMock()
    mock_response.text = "Valid response"
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    # Create history with invalid content type
    invalid_history = [
        {"role": "user", "content": "Valid message"},
        {"role": "assistant", "content": None},  # None is not a valid string
        {"role": "user", "content": 12345}  # Number is not a valid string
    ]
    
    user_message = "Valid message"
    
    # Call function
    response = generate_response(
        user_info=mock_user,
        history=invalid_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Verify response is valid
    assert response == "Valid response"
    mock_model.start_chat.assert_called_once()
    mock_chat.send_message.assert_called_once_with(user_message)

def test_generate_response_token_limit_tracking(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test that token usage is tracked and logged during response generation"""
    mock_response = MagicMock()
    mock_response.text = "This is a response"
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    user_message = "Hello"
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]
    
    # Mock count_tokens to return predictable values
    with patch('app.llm_integration.count_tokens', return_value=10), \
         patch('app.llm_integration.logger') as mock_logger:
        
        # Call function
        response = generate_response(
            user_info=mock_user,
            history=conversation_history,
            user_message=user_message,
            products=mock_products,
            faqs=mock_faqs,
            rules=mock_rules
        )
        
        # Verify token usage was logged - use a more flexible check
        found = False
        for call_args in mock_logger.info.call_args_list:
            call_str = call_args[0][0] if call_args[0] else ""
            if "Token usage:" in call_str and "User message: 10" in call_str:
                found = True
                break
        
        assert found, "Token usage logging not found in logger calls" 

def test_generate_response_includes_product_context(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test that product information is properly included in the context sent to the LLM"""
    mock_response = MagicMock()
    mock_response.text = "Here are the products you can purchase"
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    user_message = "What products can I purchase with $500?"
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]
    
    # Call the function
    response = generate_response(
        user_info=mock_user,
        history=conversation_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Verify the model was called with product information in the context
    assert mock_model.start_chat.called
    # Get the history that was passed to start_chat
    history_arg = mock_model.start_chat.call_args[1]['history']
    # The first message should contain product information
    first_message = history_arg[0]['parts'][0]
    
    # Verify product info is in the first message
    assert "Available Products:" in first_message
    # Verify actual product names are included
    for product in mock_products:
        product_text = f"{product['name']}: {product['description']}"
        assert product_text in first_message
    
    # Also verify price information is included
    assert "$10.99" in first_message
    assert "$20.99" in first_message 

def test_generate_response_token_limit_fallback(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test that appropriate fallback message is shown when token limit is approached"""
    # Create a mock for count_tokens that returns very large token counts
    with patch('app.llm_integration.count_tokens') as mock_count_tokens:
        # Set up to return values that will exceed the token limit
        mock_count_tokens.return_value = 20000  # Very high token count
        
        user_message = "Hello"
        conversation_history = [
            {"role": "user", "content": "Previous message"}
        ]
        
        # Call function
        response = generate_response(
            user_info=mock_user,
            history=conversation_history,
            user_message=user_message,
            products=mock_products,
            faqs=mock_faqs,
            rules=mock_rules
        )
        
        # Should return token limit fallback message
        assert "conversation has become too long" in response
        assert "contact our support team" in response
        assert "support@cartoncaps.com" in response
        
        # The LLM should not have been called
        mock_model.start_chat.assert_not_called()

def test_generate_response_value_error_fallback(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test that appropriate fallback message is shown when a ValueError is raised"""
    # Set up mock to raise ValueError with token limit message
    mock_model.start_chat.side_effect = ValueError("Token limit exceeded for the conversation")
    
    user_message = "Hello"
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]
    
    # Call function
    response = generate_response(
        user_info=mock_user,
        history=conversation_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Should return token limit fallback message
    assert "conversation has become too long" in response
    assert "contact our support team" in response
    assert "support@cartoncaps.com" in response

def test_generate_response_general_error_fallback(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test that appropriate fallback message is shown when a general error occurs"""
    # Set up mock to raise a general error
    mock_model.start_chat.side_effect = Exception("General API Error")
    
    user_message = "Hello"
    conversation_history = [
        {"role": "user", "content": "Hi"}
    ]
    
    # Call function
    response = generate_response(
        user_info=mock_user,
        history=conversation_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Should return general error fallback message
    assert "trouble generating a response" in response
    assert "try again in a moment" in response
    assert "support@cartoncaps.com" in response

def test_generate_response_empty_response_fallback(mock_model, mock_user, mock_products, mock_faqs, mock_rules):
    """Test that appropriate fallback message is shown when an empty response is returned"""
    mock_response = MagicMock()
    mock_response.text = ""  # Empty response
    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response
    mock_model.start_chat.return_value = mock_chat
    
    user_message = "Hello"
    conversation_history = [{"role": "user", "content": "Hi"}]
    
    # Call function
    response = generate_response(
        user_info=mock_user,
        history=conversation_history,
        user_message=user_message,
        products=mock_products,
        faqs=mock_faqs,
        rules=mock_rules
    )
    
    # Should return empty response fallback message
    assert "received an empty response" in response
    assert "support@cartoncaps.com" in response 