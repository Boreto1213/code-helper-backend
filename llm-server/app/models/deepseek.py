from typing import Dict
from pydantic import BaseModel

class PromptRequest(BaseModel):
    content: Dict
    pr_url: str
    pr_info: Dict
    
    class Config:
        max_length = None
        
    def __init__(self, **data):
        super().__init__(**data)
        
class LLMReviewData(BaseModel):
    generated_text: str
    pr_url: str
    
    def __init__(self, **data):
        super().__init__(**data)
        
class DeepSeekResponse(BaseModel):
    generated_text: str
    
    def __init__(self, **data):
        super().__init__(**data)