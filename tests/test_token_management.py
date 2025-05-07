import pytest
from unittest.mock import patch, MagicMock
from app.llm_integration import count_tokens, truncate_history_by_tokens

# Test the token counting function
def test_count_tokens_with_tiktoken():
    """Test token counting with tiktoken available"""
    # Mock tokenizer to return a specific number of tokens
    mock_tokenizer = MagicMock()
    mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
    
    with patch('app.llm_integration.tokenizer', mock_tokenizer):
        # Test with normal text
        assert count_tokens("This is a test") == 5
        mock_tokenizer.encode.assert_called_with("This is a test")
        
        # Test with empty text
        assert count_tokens("") == 0
        
        # Test with None
        assert count_tokens(None) == 0

def test_count_tokens_fallback():
    """Test token counting with fallback method (no tiktoken)"""
    with patch('app.llm_integration.tokenizer', None):
        # Test with normal text (approx 4 chars per token)
        assert count_tokens("This is a test") == 3  # 14 chars / 4 = 3.5 -> 3
        
        # Test with empty text
        assert count_tokens("") == 0
        
        # Test with None
        assert count_tokens(None) == 0
        
        # Test with longer text
        long_text = "A" * 100
        assert count_tokens(long_text) == 25  # 100 chars / 4 = 25

# Test the history truncation function
def test_truncate_history_empty():
    """Test truncation with empty history"""
    system_prompt = "You are an AI assistant"
    
    with patch('app.llm_integration.count_tokens', return_value=5):
        history, tokens = truncate_history_by_tokens([], system_prompt)
        assert history == []
        assert tokens == 5  # Just the system prompt tokens

def test_truncate_history_under_limit():
    """Test truncation when history is under the token limit"""
    system_prompt = "System prompt"
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm good!"}
    ]
    
    # Mock token counts: 10 for system, 5 for each message
    def mock_count_tokens(text):
        if text == system_prompt:
            return 10
        return 5
    
    with patch('app.llm_integration.count_tokens', side_effect=mock_count_tokens):
        truncated, tokens = truncate_history_by_tokens(
            history, 
            system_prompt,
            max_tokens=100,  # High limit
            target_tokens=80
        )
        
        # Should keep all messages
        assert len(truncated) == 4
        assert tokens == 30  # 10 (system) + 4 * 5 (messages)

def test_truncate_history_over_limit():
    """Test truncation when history exceeds the token limit"""
    system_prompt = "System prompt"
    
    # Create 10 messages with alternating roles
    history = []
    for i in range(10):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": f"Message {i+1}"})
    
    # Mock token counting to return increasing values based on message index
    def mock_count_tokens(text):
        if text == system_prompt:
            return 20
        
        # Extract message number if possible
        if "Message " in text:
            try:
                num = int(text.split("Message ")[1])
                return num * 10  # Message 1 = 10 tokens, Message 2 = 20 tokens, etc.
            except (IndexError, ValueError):
                pass
        
        return 10  # Default for other text
    
    with patch('app.llm_integration.count_tokens', side_effect=mock_count_tokens):
        # Set a limit that will force truncation
        truncated, tokens = truncate_history_by_tokens(
            history,
            system_prompt,
            max_tokens=200,
            target_tokens=180
        )
        
        # Should keep most recent messages prioritizing smaller ones
        assert len(truncated) < 10
        
        # Last 5 messages would be too many tokens, so it should prioritize 
        # keeping smaller messages up to the available tokens
        assert tokens <= 200

def test_truncate_recent_messages_over_limit():
    """Test when even recent messages exceed the token limit"""
    system_prompt = "System prompt"
    
    # Create 5 messages with very large token counts
    history = []
    for i in range(5):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": f"Large message {i+1}"})
    
    # Mock token counting - system takes 20, each message takes 100
    def mock_count_tokens(text):
        if text == system_prompt:
            return 20
        return 100  # Very large messages
    
    with patch('app.llm_integration.count_tokens', side_effect=mock_count_tokens):
        # Set a limit that can't fit all recent messages
        truncated, tokens = truncate_history_by_tokens(
            history,
            system_prompt,
            max_tokens=250,  # Can only fit 2 messages + system prompt
            target_tokens=230
        )
        
        # Should keep only the messages that fit
        assert len(truncated) <= 2
        assert tokens <= 250

def test_truncate_history_non_string_content():
    """Test truncation with non-string content in messages"""
    system_prompt = "System prompt"
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": None},  # None instead of string
        {"role": "user", "content": 12345},  # Number instead of string
        {"role": "assistant", "content": {"key": "value"}}  # Dict instead of string
    ]
    
    # Mock token counting
    def mock_count_tokens(text):
        if text == system_prompt:
            return 10
        if text == "Hello":
            return 5
        if text == "None":
            return 4
        if text == "12345":
            return 5
        if text == "{'key': 'value'}":
            return 15
        return 5  # Default
    
    with patch('app.llm_integration.count_tokens', side_effect=mock_count_tokens):
        truncated, tokens = truncate_history_by_tokens(
            history, 
            system_prompt,
            max_tokens=100
        )
        
        # Should handle non-string content by converting to string
        assert len(truncated) == 4
        assert tokens <= 100 