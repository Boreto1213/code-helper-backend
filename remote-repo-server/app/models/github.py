from pydantic import BaseModel
from typing import Optional

class Comment:
    def __init__(self, file: str, line: int, message: str, suggestion: Optional[str] = None):
        self.file = file
        self.line = line
        self.message = message
        self.suggestion = suggestion

class PromptRequest(BaseModel):
    content: str
    pr_url: Optional[str] = None  # Add PR URL for GitHub API calls
    
    class Config:
        # Allow arbitrary length strings
        max_length = None
        
class LLMReviewData(BaseModel):
    generated_text: str
    pr_url: str