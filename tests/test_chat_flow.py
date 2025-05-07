import pytest
import httpx
from httpx import ASGITransport
from app.main import app 
from fastapi import status

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="function")
async def async_client():
    """Provides an asynchronous test client for the FastAPI app"""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

async def test_new_conversation_referral_followup(async_client: httpx.AsyncClient):
    """
    Tests starting a new conversation about referrals and following up
    within the same conversation context
    """
    test_user_id = 1  # Assuming a test user with ID 1 exists or is mocked

    # 1. Start a new conversation (no conversation_id)
    initial_message = "Hi, how does the referral program work?"
    response1 = await async_client.post(
        "/chat",
        json={
            "user_id": test_user_id,
            "message": initial_message,
            # No conversation_id provided to start a new one
        }
    )

    # Assertions for the first response
    assert response1.status_code == status.HTTP_200_OK
    response1_data = response1.json()
    assert "conversation_id" in response1_data
    assert isinstance(response1_data["conversation_id"], str)
    assert "response" in response1_data
    assert isinstance(response1_data["response"], str)

    conversation_id = response1_data["conversation_id"]

    # 2. Follow up in the same conversation
    followup_message = "And do my friends get a discount?"
    response2 = await async_client.post(
        "/chat",
        json={
            "user_id": test_user_id,
            "message": followup_message,
            "conversation_id": conversation_id
        }
    )

    # Assertions for the second response
    assert response2.status_code == status.HTTP_200_OK
    response2_data = response2.json()
    assert "response" in response2_data
    assert isinstance(response2_data["response"], str)
    # Check if the response mentions friends/discount (context check)
    # This assertion depends heavily on the (mocked) LLM's ability
    # assert "friend" in response2_data["response"].lower() or "discount" in response2_data["response"].lower()

    # Ensure the conversation ID hasn't changed unexpectedly
    assert response2_data.get("conversation_id") == conversation_id 