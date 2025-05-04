from app.utils.general import parse_review_comments
from fastapi import FastAPI, HTTPException, Response
import os
from dotenv import load_dotenv
from app.models.github import LLMReviewData
from app.services.github import ReviewBot

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 