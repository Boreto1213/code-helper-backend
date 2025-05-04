import pytest
from fastapi.testclient import TestClient
from main import app
import databases
import sqlalchemy
from datetime import datetime
import os

# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test_users.db"
test_database = databases.Database(TEST_DATABASE_URL)
test_metadata = sqlalchemy.MetaData()

# Test user table definition
test_users = sqlalchemy.Table(
    "users",
    test_metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True),
    sqlalchemy.Column("full_name", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

# Test client
client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_database():
    # Override the database URL for testing
    app.dependency_overrides[databases.Database] = lambda: test_database
    
    # Create test database
    engine = sqlalchemy.create_engine(TEST_DATABASE_URL)
    test_metadata.create_all(engine)
    
    yield
    
    # Clean up after tests
    test_metadata.drop_all(engine)
    if os.path.exists("test_users.db"):
        os.remove("test_users.db")

# Test data
test_user = {
    "email": "test@example.com",
    "username": "testuser",
    "full_name": "Test User"
}

test_user_update = {
    "full_name": "Updated Test User"
}

# Test cases
def test_create_user():
    response = client.post("/users/", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["username"] == test_user["username"]
    assert data["full_name"] == test_user["full_name"]
    assert "id" in data
    assert "created_at" in data

def test_create_duplicate_user():
    # Create first user
    client.post("/users/", json=test_user)
    
    # Try to create duplicate
    response = client.post("/users/", json=test_user)
    assert response.status_code == 409
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "DUPLICATE_ENTRY"

def test_get_users():
    # Create a user
    client.post("/users/", json=test_user)
    
    # Get all users
    response = client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == test_user["email"]

def test_get_user():
    # Create a user
    create_response = client.post("/users/", json=test_user)
    user_id = create_response.json()["id"]
    
    # Get the user
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["username"] == test_user["username"]

def test_get_nonexistent_user():
    response = client.get("/users/999")
    assert response.status_code == 404
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "NOT_FOUND"

def test_update_user():
    # Create a user
    create_response = client.post("/users/", json=test_user)
    user_id = create_response.json()["id"]
    
    # Update the user
    response = client.put(f"/users/{user_id}", json=test_user_update)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == test_user_update["full_name"]
    assert data["email"] == test_user["email"]  # Email should remain unchanged

def test_update_nonexistent_user():
    response = client.put("/users/999", json=test_user_update)
    assert response.status_code == 404
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "NOT_FOUND"

def test_update_user_no_fields():
    # Create a user
    create_response = client.post("/users/", json=test_user)
    user_id = create_response.json()["id"]
    
    # Try to update with no fields
    response = client.put(f"/users/{user_id}", json={})
    assert response.status_code == 400
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "BAD_REQUEST"

def test_delete_user():
    # Create a user
    create_response = client.post("/users/", json=test_user)
    user_id = create_response.json()["id"]
    
    # Delete the user
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"
    
    # Verify user is deleted
    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_user():
    response = client.delete("/users/999")
    assert response.status_code == 404
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "NOT_FOUND"

def test_validation_error():
    # Test with invalid email
    invalid_user = {
        "email": "invalid-email",
        "username": "testuser",
        "full_name": "Test User"
    }
    response = client.post("/users/", json=invalid_user)
    assert response.status_code == 422
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "VALIDATION_ERROR"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200 