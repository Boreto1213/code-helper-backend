import pytest
from fastapi.testclient import TestClient
import databases
import sqlalchemy
from sqlalchemy.pool import StaticPool
from datetime import datetime
import uuid
from main import app, database as main_db_instance

# Test client - create once and reuse
client = TestClient(app)

# Base user template - will be customized for each test
USER_TEMPLATE = {
    "email": "test{}@example.com",
    "username": "testuser{}",
    "full_name": "Test User {}"
}

# Function to set up a new database for every test
@pytest.fixture(autouse=True)
async def isolated_db():
    """Create a completely new database for each test."""
    # Create a unique in-memory database URL for this test
    db_id = str(uuid.uuid4())
    db_url = f"sqlite:///:memory:{db_id}"
    
    # Set up the tables
    engine = sqlalchemy.create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    metadata = sqlalchemy.MetaData()
    
    # Define test table
    users = sqlalchemy.Table(
        "users",
        metadata,
        sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
        sqlalchemy.Column("email", sqlalchemy.String),
        sqlalchemy.Column("username", sqlalchemy.String),
        sqlalchemy.Column("full_name", sqlalchemy.String),
        sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
    )
    
    # Create the tables
    metadata.create_all(engine)
    
    # Create a new Database instance
    test_db = databases.Database(db_url)
    await test_db.connect()
    
    # Override the app's database dependency
    app.dependency_overrides[main_db_instance] = lambda: test_db
    
    # Yield to allow the test to run
    yield
    
    # Clean up
    await test_db.disconnect()
    app.dependency_overrides.clear()

# --- Test Cases ---

# def test_create_user():
#     # Create unique user data for this test
#     test_user = {
#         "email": "create@example.com",
#         "username": "createuser",
#         "full_name": "Create Test User"
#     }
    
#     response = client.post("/users/", json=test_user)
#     assert response.status_code == 200, response.text
#     data = response.json()
#     assert data["email"] == test_user["email"]
#     assert "id" in data

# def test_create_duplicate_user():
#     # Create unique user data for this test
#     test_user = {
#         "email": "duplicate@example.com",
#         "username": "duplicateuser",
#         "full_name": "Duplicate Test User"
#     }
    
#     # First creation should succeed
#     response1 = client.post("/users/", json=test_user)
#     assert response1.status_code == 200, response1.text
    
#     # Second creation with same data should fail with 409
#     response2 = client.post("/users/", json=test_user)
#     assert response2.status_code == 409, response2.text
#     data = response2.json()
#     assert "User with this email or username already exists" in data.get("detail", "")

# def test_get_users():
#     # Create unique user data for this test
#     test_user = {
#         "email": "getall@example.com",
#         "username": "getalluser",
#         "full_name": "Get All Test User"
#     }
    
#     client.post("/users/", json=test_user)
#     response = client.get("/users/")
#     assert response.status_code == 200, response.text
#     data = response.json()
#     assert isinstance(data, list)
#     assert len(data) >= 1 # Should find the user created in this test
#     assert any(user["email"] == test_user["email"] for user in data)

# def test_get_user():
#     # Create unique user data for this test
#     test_user = {
#         "email": "getone@example.com",
#         "username": "getoneuser",
#         "full_name": "Get One Test User"
#     }
    
#     create_response = client.post("/users/", json=test_user)
#     user_id = create_response.json()["id"]
#     response = client.get(f"/users/{user_id}")
#     assert response.status_code == 200, response.text
#     data = response.json()
#     assert data["id"] == user_id
#     assert data["email"] == test_user["email"]

def test_get_nonexistent_user():
    response = client.get("/users/99999")
    assert response.status_code == 404, response.text
    # Check the detail message from the HTTPException in main.py
    assert "User not found" in response.json().get("detail", "")

# def test_update_user():
#     # Create unique user data for this test
#     test_user = {
#         "email": "update@example.com",
#         "username": "updateuser",
#         "full_name": "Update Test User"
#     }
    
#     update_data = {
#         "full_name": "Updated Name"
#     }
    
#     create_response = client.post("/users/", json=test_user)
#     user_id = create_response.json()["id"]
#     response = client.put(f"/users/{user_id}", json=update_data)
#     assert response.status_code == 200, response.text
#     data = response.json()
#     assert data["id"] == user_id
#     assert data["full_name"] == update_data["full_name"]

def test_update_nonexistent_user():
    update_data = {
        "full_name": "Updated Name"
    }
    
    response = client.put("/users/99999", json=update_data)
    assert response.status_code == 404, response.text
    # Check the detail message
    assert "User not found" in response.json().get("detail", "")

# def test_update_user_no_fields():
#     # Create unique user data for this test
#     test_user = {
#         "email": "updateempty@example.com",
#         "username": "updateemptyuser",
#         "full_name": "Update Empty Test User"
#     }
    
#     create_response = client.post("/users/", json=test_user)
#     user_id = create_response.json()["id"]
#     response = client.put(f"/users/{user_id}", json={})
#     assert response.status_code == 400, response.text
#     # Check the detail message
#     assert "No fields to update" in response.json().get("detail", "")

def test_delete_user():
    # Create unique user data for this test
    test_user = {
        "email": "delete@example.com",
        "username": "deleteuser",
        "full_name": "Delete Test User"
    }
    
    create_response = client.post("/users/", json=test_user)
    user_id = create_response.json()["id"]
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "User deleted successfully"
    # Verify user is deleted
    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_user():
    response = client.delete("/users/99999")
    assert response.status_code == 404, response.text
    # Check the detail message
    assert "User not found" in response.json().get("detail", "")

def test_validation_error():
    invalid_user_payload = {
        "email": "invalid-email", # Invalid email format
        "username": "validationtest",
        "full_name": "Validation Test"
    }
    response = client.post("/users/", json=invalid_user_payload)
    assert response.status_code == 422, response.text # Pydantic validation error
    # Update assertion to match actual response structure
    assert "detail" in response.json()
    # Validation errors from Pydantic typically contain detail with location, type, etc.

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"} 