from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from producer import send_message

app = FastAPI()

# Load environment variables
load_dotenv()

# Add GitHub token for API access
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Service URLs
REMOTE_REPO_SERVER_URL = os.getenv("REMOTE_REPO_SERVER_URL")

# Your webhook secret (set this in your environment variables in production)
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

# Kafka topic for PR changes
PR_CHANGES_TOPIC = "pr-changes"

class PullRequestPayload(BaseModel):
    action: str
    number: int
    pull_request: dict
    repository: dict
    sender: dict

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify that the webhook payload was sent from GitHub"""
    if not signature_header:
        return False

    # Get the signature from the header
    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False

    # Create our own signature
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

@app.get("/")
async def root():
    return {"message": "Webhook server is running"}

@app.post("/webhook")
async def github_webhook(request: Request):
    # Get the signature from headers
    signature_header = request.headers.get('x-hub-signature-256')
    event_type = request.headers.get('x-github-event')
    
    # Get the raw request body
    body = await request.body()
    
    # Verify webhook signature
    if not verify_signature(body, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse the payload
    payload = json.loads(body)

    # Handle pull request events
    if event_type == 'pull_request':
        pr_data = PullRequestPayload(**payload)
        
        # Handle different PR actions
        if pr_data.action == 'opened' or pr_data.action == 'reopened':
            # Get basic PR info
            pr_info = {
                "number": pr_data.number,
                "title": pr_data.pull_request.get('title', ''),
                "author": pr_data.pull_request.get('user', {}).get('login', ''),
                "base_branch": pr_data.pull_request.get('base', {}).get('ref', ''),
                "head_branch": pr_data.pull_request.get('head', {}).get('ref', '')
            }
            print(f"PR #{pr_data.number} was opened")
            print(pr_info)
            
            
            try:
                send_message(PR_CHANGES_TOPIC, {
                    "pr_url": pr_data.pull_request.get('url', ''),
                    "pr_info": pr_info
                })
                print(f"PR change message sent to Kafka topic: {PR_CHANGES_TOPIC}")
                
            except Exception as e:
                print(f"Error sending PR change to Kafka: {str(e)}")
                import traceback
                print(traceback.format_exc())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)