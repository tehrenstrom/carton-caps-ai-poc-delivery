import pytest
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test env before tests"""
    os.environ["TESTING"] = "True"
    
    yield
    
    os.environ.pop("TESTING", None) 