from sqlalchemy.pool import StaticPool
from main import app, database as main_db_instance

TEST_DATABASE_URL = "sqlite:///:memory:"

# Configure the test database instance
# Use an in-memory DB with StaticPool so the same connection is reused across tests
test_database = databases.Database(TEST_DATABASE_URL, force_rollback=True)

# Pytest fixture to set up and tear down the database structure for the test session
@pytest.fixture(scope="session", autouse=True)
def setup_test_database_structure():
    """Creates and drops the test database tables once per session."""
    engine = sqlalchemy.create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_metadata.create_all(bind=engine)
    yield
    test_metadata.drop_all(bind=engine)

# ... rest of file remains unchanged ... 