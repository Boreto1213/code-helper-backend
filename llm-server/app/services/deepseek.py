import httpx
import os
from app.models.deepseek import DeepSeekResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

    async def get_client(self) -> httpx.AsyncClient:
        """Creates and returns an async HTTP client with the DeepSeek API headers"""
        return httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0  # Increased timeout for potentially long DeepSeek requests
        )

    async def process_prompt(self, prompt: str) -> DeepSeekResponse:
        """Process a prompt through the DeepSeek API"""
        async with await self.get_client() as client:
            try:
                # Configure the request to DeepSeek API
                deepseek_request = {
                    "model": "deepseek-coder",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000  # Increased for longer reviews
                }
                
                # Make request to DeepSeek API
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    json=deepseek_request
                )
                
                # Check if the request was successful
                response.raise_for_status()
                data = response.json()
                
                # Log the response to console
                print("\nDeepSeek API Response:")
                print(data["choices"][0]["message"]["content"])
                
                return DeepSeekResponse(
                    generated_text=data["choices"][0]["message"]["content"]
                )
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"DeepSeek API error: {e.response.text}")
            except Exception as e:
                raise Exception(f"Error processing request: {str(e)}") 