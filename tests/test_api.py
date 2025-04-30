import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatRequest, ChatResponse, Product, FAQ, ReferralRule
from app import crud
from app.llm_integration import generate_response
import os
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock, AsyncMock
import time
import asyncio
import httpx # Import httpx for async client
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

# Create a test client
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

# ---- Patched db functions ---- #

# Redefine mock database functions as direct test fixtures
@pytest.fixture
def mock_db_functions(mock_user, mock_products, mock_faqs, mock_rules):
    """Create simple async mock functions for database operations"""
    
    # Keep track of test entities during test session
    mock_db = {
        "products": {123: {"id": 123, "name": "Test Product", "description": "Description", "price": 10.0}},
        "faqs": {456: {"id": 456, "question": "Test Question", "answer": "Test Answer"}}
    }
    
    # Create async versions of all the database functions we need
    async def mock_get_user(session, user_id):
        if user_id == 999999:  # Special case for the "not found" test
            return None
        return mock_user
        
    async def mock_get_products(session, limit=100):
        return mock_products[:limit]
        
    async def mock_get_referral_faqs(session):
        return mock_faqs
        
    async def mock_get_referral_rules(session):
        return mock_rules
    
    async def mock_get_conversation_history_db(session, conversation_id):
        return []
    
    async def mock_add_conversation_message(session, user_id, conversation_id, sender, message):
        return None
    
    async def mock_create_product(session, name, description, price):
        product_id = 123  # Hardcoded ID for testing
        product = {"id": product_id, "name": name, "description": description, "price": price}
        mock_db["products"][product_id] = product
        return product
    
    async def mock_get_product_by_id(session, product_id):
        return mock_db["products"].get(product_id)
    
    async def mock_update_product(session, product_id, name, description, price):
        if product_id not in mock_db["products"]:
            return None
        product = {"id": product_id, "name": name, "description": description, "price": price}
        mock_db["products"][product_id] = product
        return product
    
    async def mock_delete_product(session, product_id):
        if product_id not in mock_db["products"]:
            return False
        del mock_db["products"][product_id]
        return True
    
    async def mock_create_faq(session, question, answer):
        faq_id = 456  # Hardcoded ID for testing
        faq = {"id": faq_id, "question": question, "answer": answer}
        mock_db["faqs"][faq_id] = faq
        return faq
        
    async def mock_get_faq_by_id(session, faq_id):
        return mock_db["faqs"].get(faq_id)
    
    async def mock_update_faq(session, faq_id, question, answer):
        if faq_id not in mock_db["faqs"]:
            return None
        faq = {"id": faq_id, "question": question, "answer": answer}
        mock_db["faqs"][faq_id] = faq
        return faq
    
    async def mock_delete_faq(session, faq_id):
        if faq_id not in mock_db["faqs"]:
            return False
        del mock_db["faqs"][faq_id]
        return True
        
    async def mock_create_referral_rule(session, rule):
        return rule
        
    # Return all mock functions in a dict
    return {
        "get_user": mock_get_user,
        "get_products": mock_get_products,
        "get_referral_faqs": mock_get_referral_faqs,
        "get_referral_rules": mock_get_referral_rules,
        "get_conversation_history_db": mock_get_conversation_history_db,
        "add_conversation_message": mock_add_conversation_message,
        "create_product": mock_create_product,
        "get_product_by_id": mock_get_product_by_id,
        "update_product": mock_update_product,
        "delete_product": mock_delete_product,
        "create_faq": mock_create_faq,
        "get_faq_by_id": mock_get_faq_by_id,
        "update_faq": mock_update_faq,
        "delete_faq": mock_delete_faq,
        "create_referral_rule": mock_create_referral_rule
    }

# Apply mock functions to override crud functions for all tests
@pytest.fixture(autouse=True)
def patch_crud_functions(mock_db_functions):
    """Patch all crud functions with our mock versions"""
    
    # Create patches for all the functions
    patches = []
    for func_name, mock_func in mock_db_functions.items():
        patch_path = f"app.crud.{func_name}"
        patches.append(patch(patch_path, mock_func))
    
    # Apply all patches
    for p in patches:
        p.start()
    
    yield
    
    # Stop all patches
    for p in patches:
        p.stop()

def test_chat_endpoint_logic_with_mocked_llm():
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
            "user_id": 999999,  # This will trigger the "not found" case in our mock
            "message": "Hello",
            "conversation_id": "test-error-conv"
        }
    )
    
    assert response.status_code == 404

def test_get_products_endpoint():
    """Test GET /products endpoint."""
    response = client.get("/products?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

@pytest.mark.asyncio
async def test_create_referral_rule_endpoint():
    """Test POST referral-rules endpoint using async client"""
    unique_ts = int(time.time() * 1000)
    rule_text = f"API Test Rule {unique_ts}"
    
    # Use the async client
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
        rule_data = {"rule": rule_text}
        response = await async_client.post("/referral-rules", json=rule_data)
        assert response.status_code == 200
        data = response.json()
        assert data["rule"] == rule_text

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

# --- New Async Test --- #

@pytest.mark.asyncio 
async def test_chat_endpoint_is_async():
    """Tests if the /chat endpoint handles concurrent requests asynchronously."""
    SLEEP_DURATION = 0.2  # seconds
    NUM_REQUESTS = 3
    original_add_message = crud.add_conversation_message
    call_count = 0

    async def mock_add_message_with_sleep(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 2 != 0: 
             print(f"Mock add_message sleeping for {SLEEP_DURATION}s (call {call_count})")
             await asyncio.sleep(SLEEP_DURATION)
        else:
             print(f"Mock add_message returning immediately (call {call_count})")
        return 

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
        with patch('app.crud.add_conversation_message', new=mock_add_message_with_sleep), \
             patch('app.llm_integration.generate_response', return_value="Mock LLM Response"), \
             patch('app.crud.get_user', return_value={'id': 1, 'name': 'Test User', 'school_name': 'Test School'}), \
             patch('app.crud.get_conversation_history_db', return_value=[]), \
             patch('app.crud.get_products', return_value=[{'id': 1, 'name': 'Mock Prod', 'description': 'Desc', 'price': 1.0}]), \
             patch('app.crud.get_referral_faqs', return_value=[{'id': 1, 'question': 'Q', 'answer': 'A'}]), \
             patch('app.crud.get_referral_rules', return_value=["Mock Rule 1"]):
            
            tasks = []
            for i in range(NUM_REQUESTS):
                payload = {
                    "user_id": 1,
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