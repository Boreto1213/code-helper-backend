from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError
from typing import List, Optional
import databases
import sqlalchemy
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# User table definition
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True),
    sqlalchemy.Column("full_name", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

# Pydantic models for request/response
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# Error response models
class ErrorResponse(BaseModel):
    detail: str
    error_code: str

# Create FastAPI app
app = FastAPI(
    title="User Management API",
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        409: {"model": ErrorResponse, "description": "Conflict"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)



# Database connection
@app.on_event("startup")
async def startup():
    try:
        await database.connect()
        engine = sqlalchemy.create_engine(DATABASE_URL)
        metadata.create_all(engine)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    try:
        await database.disconnect()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error during database shutdown: {e}")

# CRUD operations
@app.post("/users/", response_model=User, responses={
    409: {"description": "User with this email or username already exists"},
    500: {"description": "Internal server error"}
})
async def create_user(user: UserCreate):
    try:
        query = users.insert().values(
            email=user.email,
            username=user.username,
            full_name=user.full_name
        )
        last_record_id = await database.execute(query)
        logger.info(f"User created successfully with ID: {last_record_id}")
        return {**user.dict(), "id": last_record_id, "created_at": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise

@app.get("/users/", response_model=List[User], responses={
    500: {"description": "Internal server error"}
})
async def read_users(skip: int = 0, limit: int = 100):
    try:
        query = users.select().offset(skip).limit(limit)
        return await database.fetch_all(query)
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise

@app.get("/users/{user_id}", response_model=User, responses={
    404: {"description": "User not found"},
    500: {"description": "Internal server error"}
})
async def read_user(user_id: int):
    try:
        query = users.select().where(users.c.id == user_id)
        user = await database.fetch_one(query)
        if user is None:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise

@app.put("/users/{user_id}", response_model=User, responses={
    400: {"description": "No fields to update"},
    404: {"description": "User not found"},
    409: {"description": "User with this email or username already exists"},
    500: {"description": "Internal server error"}
})
async def update_user(user_id: int, user: UserUpdate):
    try:
        # Check if user exists
        existing_user = await read_user(user_id)
        
        query = users.update().where(users.c.id == user_id)
        values = {k: v for k, v in user.dict().items() if v is not None}
        if not values:
            logger.warning("No fields provided for update")
            raise HTTPException(status_code=400, detail="No fields to update")
        
        query = query.values(**values)
        await database.execute(query)
        logger.info(f"User updated successfully with ID: {user_id}")
        return await read_user(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise

@app.delete("/users/{user_id}", responses={
    404: {"description": "User not found"},
    500: {"description": "Internal server error"}
})
async def delete_user(user_id: int):
    try:
        # Check if user exists
        await read_user(user_id)
        
        query = users.delete().where(users.c.id == user_id)
        result = await database.execute(query)
        if not result:
            logger.warning(f"User not found for deletion with ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"User deleted successfully with ID: {user_id}")
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise

# Health check endpoint
@app.get("/health", status_code=200)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
