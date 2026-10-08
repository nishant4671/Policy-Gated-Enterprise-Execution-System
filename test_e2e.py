import uuid
import time
from mock_systems.api import app, get_db
from fastapi.testclient import TestClient

client = TestClient(app)
print('Testing End-to-End...')
