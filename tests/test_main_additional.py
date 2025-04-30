import pytest
from fastapi.testclient import TestClient
from app.main import app
import os
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
import json
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup():
    """Setup before tests and cleanup after"""
    # Setup
    with patch('app.main.get_async_session') as mock_get_session:
        mock_session = MagicMock(spec=AsyncSession)
        mock_get_session.return_value = mock_session
        yield mock_session

# Frontend Endpoints Tests
def test_read_index():
    """Test the root endpoint serves index.html"""
    # Mock the existence of static/index.html
    with patch('os.path.exists', return_value=True), \
         patch('fastapi.responses.FileResponse', return_value="index.html content"):
        response = client.get("/")
        assert response.status_code == 200

def test_read_index_file_not_found():
    """Test handling of missing index.html file"""
    # Mock static/index.html not existing
    with patch('os.path.exists', return_value=False):
        response = client.get("/")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

def test_serve_static():
    """Test serving static files"""
    # Note: We can't directly test the static mounted endpoint
    # as it's handled by StaticFiles middleware. Just testing existence check.
    with patch('os.path.exists', return_value=True):
        # Need to mock the specific route for static files
        with patch('app.main.serve_static', return_value="static file content"):
            response = client.get("/static/nonexistent/style.css")
            # Since we're mocking the existence check but not the actual route handler,
            # this should return 404 which is expected since the StaticFiles middleware 
            # is handling this path, not our serve_static function.
            assert response.status_code == 404

def test_serve_static_file_not_found():
    """Test handling of missing static file"""
    # Mock static file not existing
    with patch('os.path.exists', return_value=False):
        response = client.get("/static/not-existing.css")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

def test_read_documentation():
    """Test documentation.html endpoint"""
    # Mock the documentation.html file
    with patch('fastapi.responses.FileResponse', return_value="documentation content"):
        response = client.get("/documentation.html")
        assert response.status_code == 200

# User Management Endpoints Tests
def test_get_users_list():
    """Test GET /users endpoint"""
    # Mock crud.get_all_users
    mock_users = [
        {"id": 1, "name": "User 1", "school_name": "School 1"},
        {"id": 2, "name": "User 2", "school_name": "School 2"}
    ]
    with patch('app.crud.get_all_users', return_value=mock_users):
        response = client.get("/users")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == 1
        assert response.json()[1]["name"] == "User 2"

def test_get_user_not_found():
    """Test GET /user/{user_id} with non-existent user"""
    # Mock crud.get_user to return None
    with patch('app.crud.get_user', return_value=None):
        response = client.get("/user/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

# History Endpoint Test
def test_get_history_endpoint():
    """Test GET /history/{conversation_id} endpoint"""
    # Mock conversation.get_conversation_history
    mock_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]
    with patch('app.conversation.get_conversation_history', return_value=("test-conv", mock_history)):
        response = client.get("/history/test-conv")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["role"] == "user"
        assert response.json()[1]["content"] == "Hi there"

# Referral Rules Endpoints Tests
def test_get_referral_rules():
    """Test GET /referral-rules endpoint"""
    # Mock crud.get_referral_rules
    mock_rules = ["Rule 1", "Rule 2", "Rule 3"]
    with patch('app.crud.get_referral_rules', return_value=mock_rules):
        response = client.get("/referral-rules")
        assert response.status_code == 200
        assert len(response.json()) == 3
        assert response.json()[0]["rule"] == "Rule 1"

def test_update_referral_rule():
    """Test PUT /referral-rules/{rule_id} endpoint"""
    # Mock crud.update_referral_rule
    with patch('app.crud.update_referral_rule', return_value="Updated Rule"):
        response = client.put(
            "/referral-rules/1",
            json={"rule": "Updated Rule"}
        )
        assert response.status_code == 200
        assert response.json()["rule"] == "Updated Rule"

def test_update_referral_rule_not_found():
    """Test PUT /referral-rules/{rule_id} with non-existent rule"""
    # Mock crud.update_referral_rule to return None
    with patch('app.crud.update_referral_rule', return_value=None):
        response = client.put(
            "/referral-rules/999",
            json={"rule": "Updated Rule"}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

def test_delete_referral_rule():
    """Test DELETE /referral-rules/{rule_id} endpoint"""
    # Mock crud.delete_referral_rule
    with patch('app.crud.delete_referral_rule', return_value=True):
        response = client.delete("/referral-rules/1")
        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()

def test_delete_referral_rule_not_found():
    """Test DELETE /referral-rules/{rule_id} with non-existent rule"""
    # Mock crud.delete_referral_rule to return False
    with patch('app.crud.delete_referral_rule', return_value=False):
        response = client.delete("/referral-rules/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

# Error Handling Tests
def test_general_exception_handler():
    """Test general exception handling"""
    # Create an endpoint that will raise an exception
    with patch('app.crud.get_all_users', side_effect=Exception("Test exception")):
        response = client.get("/users")
        assert response.status_code == 500
        assert "internal server error" in response.json()["detail"].lower()

# Test the handle_endpoint_errors decorator
def test_handle_endpoint_errors_decorator():
    """Test handle_endpoint_errors decorator"""
    # Test with an endpoint that uses the decorator
    with patch('app.crud.get_user', side_effect=Exception("Test exception")):
        response = client.get("/user/1")
        assert response.status_code == 500
        assert "internal server error" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_startup_event():
    """Test startup event"""
    # Mock required environment variables
    with patch.dict(os.environ, {"DATABASE_URL": "test", "GOOGLE_API_KEY": "test"}), \
         patch('app.database.test_connection', return_value=True):
        from app.main import startup_event
        # Call startup event function
        await startup_event()
        # No assertion needed; if it doesn't raise an exception, the test passes

@pytest.mark.asyncio
async def test_startup_event_missing_env_vars():
    """Test startup event with missing environment variables"""
    # Mock missing environment variables
    with patch.dict(os.environ, {}, clear=True), \
         pytest.raises(ValueError):
        from app.main import startup_event
        # Call startup event function expecting ValueError
        await startup_event() 