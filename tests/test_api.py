import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatRequest, ChatResponse, Product, FAQ, ReferralRule
from app.crud import get_user, get_products, get_referral_faqs, get_referral_rules, add_conversation_message
from app.llm_integration import generate_response
import os
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
import time

load_dotenv()

client = TestClient(app)

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
        {"id": 1, "question": "Q1", "answer": "A1"},
        {"id": 2, "question": "Q2", "answer": "A2"}
    ]

@pytest.fixture
def mock_rules():
    return ["Rule 1", "Rule 2"]

def test_chat_endpoint_logic_with_mocked_llm(mock_user, mock_products, mock_faqs, mock_rules):
    """Test the happy path logic of the /chat endpoint, mocking the LLM call."""
    with patch('app.llm_integration.generate_response', return_value="Test response"):
        response = client.post(
            "/chat",
            json={
                "user_id": 1,
                "message": "Hello",
                "conversation_id": "test-conv"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert data["response"] == "Test response"

def test_chat_endpoint_invalid_user():
    """Test /chat endpoint with an invalid user ID."""
    response = client.post(
        "/chat",
        json={
            "user_id": 999999,
            "message": "Hello",
            "conversation_id": "test-error-conv"
        }
    )
    
    assert response.status_code == 404

def test_chat_endpoint_real_db_and_llm():
    """Test /chat endpoint hitting a real database and the real LLM"""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("No database connection available")
    
    test_user_id = 1
    test_message = "What products do you have?"
    
    response = client.post(
        "/chat",
        json={
            "user_id": test_user_id,
            "message": test_message,
            "conversation_id": f"api-test-{int(time.time())}"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"] is not None
    assert len(data["response"]) > 0
    assert "conversation_id" in data
    assert data["conversation_id"] is not None

#  KB Endpoint Tests #

def test_get_products_endpoint():
    """Test GET /products endpoint."""
    response = client.get("/products?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_product_crud_cycle_endpoint():
    """Tests POST, PUT, GET /id, DELETE cycle for /products endpoint."""
    unique_ts = int(time.time() * 1000)
    product_id = None
    
    try:
        create_data = {
            "name": f"API Test CRUD Prod {unique_ts}",
            "description": "Initial Desc",
            "price": 10.00
        }
        response_create = client.post("/products", json=create_data)
        
        assert response_create.status_code == 200, f"Product creation failed: {response_create.status_code} {response_create.text}"
        
        data_create = response_create.json()
        product_id = data_create.get("id")
        assert isinstance(product_id, int), "Created product ID not found or invalid after 200 OK"
        assert data_create["name"] == create_data["name"]

        update_data = {
            "name": f"API Test CRUD Prod {unique_ts} UPDATED",
            "description": "Updated Desc",
            "price": 15.50
        }
        response_update = client.put(f"/products/{product_id}", json=update_data)
        assert response_update.status_code == 200, f"Update failed: {response_update.text}"
        data_update = response_update.json()
        assert data_update["name"] == update_data["name"]
        assert data_update["price"] == update_data["price"]

        response_get = client.get(f"/products/{product_id}")
        assert response_get.status_code == 200, f"GET by ID failed: {response_get.text}"
        data_get = response_get.json()
        assert data_get["id"] == product_id
        assert data_get["name"] == update_data["name"]

    finally:
        if product_id:
            response_delete = client.delete(f"/products/{product_id}")
            assert response_delete.status_code == 200, f"Delete failed: {response_delete.text}"
            
            response_get_after_delete = client.get(f"/products/{product_id}")
            assert response_get_after_delete.status_code == 404, "GET by ID should fail after delete"

def test_get_faqs_endpoint():
    """Test GET faqs endpoint"""
    response = client.get("/faqs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_faq_crud_cycle_endpoint():
    """Tests POST, PUT, GET /id, DELETE cycle for faqs endpoint"""
    unique_ts = int(time.time() * 1000)
    faq_id = None

    try:
        create_data = {
            "question": f"API Test CRUD Q? {unique_ts}",
            "answer": "Initial A"
        }
        response_create = client.post("/faqs", json=create_data)

        assert response_create.status_code == 200, f"FAQ creation failed: {response_create.status_code} {response_create.text}"
        
        data_create = response_create.json()
        faq_id = data_create.get("id")
        assert isinstance(faq_id, int), "Created FAQ ID not found or invalid after 200 OK"
        assert data_create["question"] == create_data["question"]

        update_data = {
            "question": f"API Test CRUD Q? {unique_ts} UPDATED",
            "answer": "Updated A"
        }
        response_update = client.put(f"/faqs/{faq_id}", json=update_data)
        assert response_update.status_code == 200, f"Update failed: {response_update.text}"
        data_update = response_update.json()
        assert data_update["question"] == update_data["question"]
        assert data_update["answer"] == update_data["answer"]

        response_get = client.get(f"/faqs/{faq_id}")
        assert response_get.status_code == 200, f"GET by ID failed: {response_get.text}"
        data_get = response_get.json()
        assert data_get["id"] == faq_id
        assert data_get["question"] == update_data["question"]

    finally:
        if faq_id:
            response_delete = client.delete(f"/faqs/{faq_id}")
            assert response_delete.status_code == 200, f"Delete failed: {response_delete.text}"
            
            response_get_after_delete = client.get(f"/faqs/{faq_id}")
            assert response_get_after_delete.status_code == 404, "GET by ID should fail after delete"

def test_get_referral_rules_endpoint():
    """Test GET referral-rules endpoint"""
    response = client.get("/referral-rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_create_referral_rule_endpoint():
    """Test POST referral-rules endpoint"""
    unique_ts = int(time.time() * 1000)
    rule_data = {"rule": f"API Test Rule {unique_ts}"}
    response = client.post("/referral-rules", json=rule_data)
    assert response.status_code == 200
    data = response.json()
    assert data["rule"] == rule_data["rule"]