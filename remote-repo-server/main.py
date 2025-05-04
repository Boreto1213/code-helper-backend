from fastapi import FastAPI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL")

app = FastAPI(title="Remote Repository API", 
              description="API for remote repository operations")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 