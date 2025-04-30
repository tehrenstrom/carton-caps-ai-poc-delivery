import pytest
import httpx
import asyncio
import time
from app.main import app
from unittest.mock import patch

@pytest.mark.asyncio
async def test_multiple_requests_concurrently():
    """Test if the API can handle multiple concurrent requests efficiently."""
    # Configuration
    NUM_REQUESTS = 10
    SLEEP_DURATION = 0.2  # seconds to simulate slow processing
    
    # Track timing for verification
    start_time = None
    end_time = None
    
    # Create a mock function that adds artificial delay
    async def mock_slow_function(*args, **kwargs):
        await asyncio.sleep(SLEEP_DURATION)
        return {}
    
    # Use async client to make concurrent requests
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
        # Apply necessary mocks
        with patch('app.crud.get_user', return_value={'id': 1, 'name': 'Test User', 'school_name': 'Test School'}), \
             patch('app.crud.get_conversation_history_db', return_value=[]), \
             patch('app.crud.add_conversation_message', new=mock_slow_function), \
             patch('app.llm_integration.generate_response', return_value="Test response"), \
             patch('app.crud.get_products', return_value=[{'id': 1, 'name': 'Product', 'description': 'Desc', 'price': 10.0}]), \
             patch('app.crud.get_referral_faqs', return_value=[{'id': 1, 'question': 'Q', 'answer': 'A'}]), \
             patch('app.crud.get_referral_rules', return_value=["Rule 1"]):
            
            # Create concurrent request tasks
            tasks = []
            for i in range(NUM_REQUESTS):
                payload = {
                    "user_id": 1,
                    "message": f"Concurrent test message {i+1}",
                    "conversation_id": f"concurrent-test-{int(time.time())}-{i}"
                }
                tasks.append(async_client.post("/chat", json=payload))
            
            # Execute requests concurrently and measure time
            start_time = time.monotonic()
            print(f"\nStarting {NUM_REQUESTS} concurrent /chat requests...")
            responses = await asyncio.gather(*tasks)
            end_time = time.monotonic()
            total_time = end_time - start_time
            print(f"Finished {NUM_REQUESTS} concurrent requests in {total_time:.4f} seconds.")
            
            # Verify all responses are successful
            for i, response in enumerate(responses):
                assert response.status_code == 200, f"Request {i+1} failed: {response.text}"
                data = response.json()
                assert "response" in data
                assert "conversation_id" in data
            
            # If the endpoint is properly async, the total time should be much less than executing serially
            serial_time_estimate = NUM_REQUESTS * SLEEP_DURATION
            assert total_time < serial_time_estimate * 0.8, \
                f"Total time ({total_time:.4f}s) suggests requests are not processed concurrently (serial would be ~{serial_time_estimate:.2f}s)"
            
            # The time should be at least as long as one request's processing time plus some overhead
            assert total_time > SLEEP_DURATION, \
                f"Total time ({total_time:.4f}s) was unexpectedly short. Check test implementation."
            
            print(f"Concurrency test passed! Processed {NUM_REQUESTS} requests in {total_time:.4f}s vs {serial_time_estimate:.2f}s serial estimate.") 