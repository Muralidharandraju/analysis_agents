import os
import shutil
import pytest
from fastapi.testclient import TestClient

import sys
import pathlib

# Ensure the app module can be imported
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def setup_teardown_knowledge_dir():
    """
    Ensures the knowledge directory exists and is empty before each test,
    and cleans up after the test.
    """
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    os.makedirs(knowledge_dir, exist_ok=True)
    # Remove all files in the knowledge directory before the test
    for item in os.listdir(knowledge_dir):
        item_path = os.path.join(knowledge_dir, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
    yield
    # Clean up after the test
    for item in os.listdir(knowledge_dir):
        item_path = os.path.join(knowledge_dir, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
