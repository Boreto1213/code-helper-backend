from fastapi import FastAPI
from dotenv import load_dotenv
import os


app = FastAPI()

# Load environment variables
load_dotenv()

# Add GitHub token for API access
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Service URLs
REMOTE_REPO_SERVER_URL = os.getenv("REMOTE_REPO_SERVER_URL")

# Your webhook secret (set this in your environment variables in production)
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

@app.get("/")
async def root():
    return {"message": "Webhook server is running"}
  
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)