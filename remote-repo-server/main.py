from app.utils.general import parse_review_comments
from fastapi import FastAPI, HTTPException, Response
import os
from dotenv import load_dotenv
from app.models.github import LLMReviewData
from app.services.github import ReviewBot
import httpx
from typing import Dict

# Load environment variables from .env file
load_dotenv()

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL")

app = FastAPI(title="Remote Repository API", 
              description="API for remote repository operations")

review_bot = ReviewBot()

@app.post("/reviews/create")
async def create_review(request: LLMReviewData):
    try:
        if request.pr_url:
            try:
                comments = parse_review_comments(request.generated_text)
                await review_bot.create_github_review(request.pr_url, comments)
                print(f"Created GitHub review with {len(comments)} comments")
            except Exception as e:
                print(f"Error creating GitHub review: {str(e)}")
        
        return Response(status_code=200)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/pr/changes")
async def get_pr_changes(request: Dict) -> Dict:
    """Fetch the PR changes from GitHub API and forward to LLM service"""
    try:
        pr_url = request.get('pr_url')
        pr_info = request.get('pr_info')
        
        if not pr_url or not pr_info:
            raise HTTPException(
                status_code=400,
                detail="Missing 'pr_url' or 'pr_info' in request"
            )
        
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Webhook"
        }
        
        async with httpx.AsyncClient() as client:
            parts = pr_url.split('/')
            owner = parts[4]
            repo = parts[5]
            pr_number = parts[7]
            files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
            
            files_response = await client.get(files_url, headers=headers)
            
            if files_response.status_code != 200:
                raise HTTPException(
                    status_code=files_response.status_code,
                    detail=f"Failed to fetch PR changes: {files_response.text}"
                )
            
            files = files_response.json()
            
            # Fetch complete file content for each changed file
            changed_files = []
            for file in files:
                contents_url = file.get('contents_url', '')
                if contents_url:
                    parts = contents_url.split('/')
                    if len(parts) >= 7:
                        owner = parts[4]
                        repo = parts[5]
                        path = '/'.join(parts[7:])
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{pr_info['head_branch']}/{path}"
                        
                        content_response = await client.get(raw_url, headers=headers)
                        if content_response.status_code == 200:
                            complete_content = content_response.text
                        else:
                            complete_content = "Could not fetch complete file content"
                    else:
                        complete_content = "Invalid contents URL format"
                else:
                    complete_content = "No contents URL available"
                
                changed_files.append({
                    "filename": file.get('filename', ''),
                    "status": file.get('status', ''),
                    "additions": file.get('additions', 0),
                    "deletions": file.get('deletions', 0),
                    "patch": file.get('patch', ''),
                    "complete_content": complete_content
                })
            
            changes = {
                "files_changed": len(files),
                "additions": sum(f.get('additions', 0) for f in files),
                "deletions": sum(f.get('deletions', 0) for f in files),
                "changed_files": changed_files
            }
            
            # Forward to LLM service
            try:
                llm_data = {
                    "content": changes,
                    "pr_url": pr_url,
                    "pr_info": pr_info
                }
                
                response = await client.post(
                    f"{os.getenv('LLM_SERVER_URL')}/process-prompt/deepseek",
                    json=llm_data
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process PR changes with LLM: {str(e)}"
                )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
    
    # To start the server, run:

    # Or alternatively:
    # uvicorn main:app --host 0.0.0.0 --port 8000 --reload
