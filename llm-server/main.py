import os
from fastapi import FastAPI, HTTPException, Response
from app.models.deepseek import PromptRequest, LLMReviewData
from app.services.deepseek import DeepSeekService
from app.services.gemini import GeminiService
from app.utils.general import create_pr_review_prompt
import httpx
import logging
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

REMOTE_REPO_SERVER_URL = os.getenv("REMOTE_REPO_SERVER_URL")


app = FastAPI(title="AI Code Review API", 
              description="API for code review using various AI models")

deepseek_service = DeepSeekService()
gemini_service = GeminiService()

@app.post("/process-prompt/deepseek")
async def process_prompt_deepseek(request: PromptRequest):
    """
    Receives a prompt as a string and forwards it to the DeepSeek API
    """
    try:
        logger.info("=== Starting DeepSeek request processing ===")

        # Create the prompt
        try:
            prompt = create_pr_review_prompt(changes=request.content, pr_info=request.pr_info)
            logger.info("Prompt created successfully")
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}", exc_info=True)
            raise
            
        # Process through DeepSeek
        try:
            logger.info("Processing prompt through DeepSeek...")
            response = await deepseek_service.process_prompt(prompt=prompt)
            logger.info("DeepSeek processing completed successfully")
        except Exception as e:
            logger.error(f"Error in DeepSeek processing: {str(e)}", exc_info=True)
            raise
        
        # If PR URL is provided, forward to remote-repo-server
        if request.pr_url:
            try:
                logger.info(f"Forwarding review to remote-repo-server for PR: {request.pr_url}")
                async with httpx.AsyncClient() as client:
                    review_data = LLMReviewData(
                        pr_url=request.pr_url,
                        generated_text=response.generated_text
                    )
                    
                    forward_response = await client.post(
                        REMOTE_REPO_SERVER_URL + "/reviews/create",
                        json=review_data.dict()
                    )
                    logger.info(f"Remote-repo-server response: {forward_response.status_code}")
                    if forward_response.status_code != 200:
                        logger.error(f"Remote-repo-server error: {forward_response.text}")
            except Exception as e:
                logger.error(f"Error forwarding to remote-repo-server: {str(e)}", exc_info=True)
                # Don't raise the error, just log it since the main processing succeeded
        
        logger.info("Request processing completed successfully")
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 