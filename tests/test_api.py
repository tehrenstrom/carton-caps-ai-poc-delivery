import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatRequest, ChatResponse, Product, FAQ, ReferralRule
from app.crud import get_user, get_products, get_referral_faqs, get_referral_rules, add_conversation_message
from app import crud # Import the crud module itself
from app.llm_integration import generate_response
import os
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
import time
import asyncio
import httpx # Import httpx for async client

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

# --- New Async Test --- #

# Use pytest.mark.asyncio for async tests
@pytest.mark.asyncio 
async def test_chat_endpoint_is_async():
    """Tests if the /chat endpoint handles concurrent requests asynchronously."""
    SLEEP_DURATION = 0.2  # seconds
    NUM_REQUESTS = 3
    
    # We need to patch an async function that is awaited inside the endpoint
    # Let's patch add_conversation_message which is awaited twice
    original_add_message = crud.add_conversation_message
    call_count = 0

    async def mock_add_message_with_sleep(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Only sleep on the first call within each request (user message save)
        # to simulate DB delay without excessive total sleep time
        if call_count % 2 != 0: 
             print(f"Mock add_message sleeping for {SLEEP_DURATION}s (call {call_count})")
             await asyncio.sleep(SLEEP_DURATION)
        else:
             print(f"Mock add_message returning immediately (call {call_count})")
        # We don't need the actual DB interaction for this test
        # await original_add_message(*args, **kwargs) # Optionally call original
        return 

    # Use httpx.AsyncClient for making async requests to the app
    # Pass the FastAPI app instance via ASGITransport
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
        # Patch all awaited calls within the endpoint flow for this test
        with patch('app.crud.add_conversation_message', new=mock_add_message_with_sleep), \
             patch('app.llm_integration.generate_response', return_value="Mock LLM Response"), \
             patch('app.crud.get_user', return_value={'id': 1, 'name': 'Test User', 'school_name': 'Test School'}), \
             patch('app.crud.get_conversation_history_db', return_value=[]), \
             patch('app.crud.get_products', return_value=[{'id': 1, 'name': 'Mock Prod', 'description': 'Desc', 'price': 1.0}]), \
             patch('app.crud.get_referral_faqs', return_value=[{'id': 1, 'question': 'Q', 'answer': 'A'}]), \
             patch('app.crud.get_referral_rules', return_value=["Mock Rule 1"]):
            
            # Prepare concurrent requests
            tasks = []
            for i in range(NUM_REQUESTS):
                payload = {
                    "user_id": 1, # Assuming user 1 exists for testing
                    "message": f"Concurrent test message {i+1}",
                    "conversation_id": f"async-test-{int(time.time())}-{i}"
                }
                tasks.append(async_client.post("/chat", json=payload))
            
            # Measure time to run requests concurrently
            start_time = time.monotonic()
            print(f"\nStarting {NUM_REQUESTS} concurrent /chat requests...")
            responses = await asyncio.gather(*tasks)
            end_time = time.monotonic()
            total_time = end_time - start_time
            print(f"Finished concurrent requests in {total_time:.4f} seconds.")

            # Check responses are successful
            for i, response in enumerate(responses):
                 assert response.status_code == 200, f"Request {i+1} failed: {response.text}"
                 data = response.json()
                 assert "response" in data
                 assert "conversation_id" in data

            # Assert that the total time is less than the serial execution time
            # Serial time would be roughly NUM_REQUESTS * SLEEP_DURATION 
            # Allow for some overhead, but it should be significantly less than serial.
            # We sleep only on odd calls, so effectively NUM_REQUESTS sleeps total.
            max_expected_serial_time = NUM_REQUESTS * SLEEP_DURATION
            # Assert total time is less than 80% of serial time (adjust threshold as needed)
            assert total_time < (max_expected_serial_time * 0.8), \
                f"Total time ({total_time:.4f}s) was not significantly less than serial time (~{max_expected_serial_time:.4f}s). Endpoint might be blocking."
            # Also assert it's at least slightly longer than one sleep, accounting for overhead
            assert total_time > SLEEP_DURATION, \
                f"Total time ({total_time:.4f}s) was unexpectedly short, check sleep logic."