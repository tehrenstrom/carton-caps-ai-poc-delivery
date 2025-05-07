import pytest
import os
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, urlunparse

from unittest.mock import AsyncMock, MagicMock

load_dotenv()

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test env before tests"""
    os.environ["TESTING"] = "True"
    
    yield
    
    os.environ.pop("TESTING", None)

@pytest.fixture
def mock_async_session():
    """Create a mock async session for testing without DB access"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = None
    execute_result.mappings.return_value.all.return_value = []
    execute_result.fetchall.return_value = []
    execute_result.scalar_one_or_none.return_value = None
    execute_result.scalar_one.return_value = None
    execute_result.scalars.return_value.all.return_value = []
    
    mock_session.execute.return_value = execute_result
    
    return mock_session

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 