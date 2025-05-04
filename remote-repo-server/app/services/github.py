from datetime import datetime, timedelta, UTC
import jwt
import httpx
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class GitHubApp:
    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        # Ensure proper PEM format
        key = private_key.strip('"').replace('\\n', '\n')
        if not key.startswith('-----BEGIN RSA PRIVATE KEY-----'):
            key = '-----BEGIN RSA PRIVATE KEY-----\n' + key
        if not key.endswith('-----END RSA PRIVATE KEY-----'):
            key = key + '\n-----END RSA PRIVATE KEY-----'
        self.private_key = key

    def generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication"""
        now = datetime.now(UTC)
        payload = {
            'iat': int(now.timestamp()),  # Issued at time
            'exp': int((now + timedelta(minutes=5)).timestamp()),  # Expires in 5 minutes (GitHub's limit)
            'iss': self.app_id
        }
        
        try:
            print("Generating JWT with payload:", payload)
            token = jwt.encode(payload, self.private_key, algorithm='RS256')
            print("Successfully generated JWT")
            return token
        except Exception as e:
            print(f"Error generating JWT: {str(e)}")
            raise Exception(f"Failed to generate JWT: {str(e)}")

    async def get_installation_token(self, installation_id: str) -> str:
        """Get an installation access token"""
        jwt_token = self.generate_jwt()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Code-Helper-App"
                }
            )
            
            if response.status_code != 201:
                raise Exception(f"Failed to get installation token: {response.text}")
            
            return response.json()['token']


class ReviewBot:
    def __init__(self):
        self.app = GitHubApp(
            app_id=os.getenv("GITHUB_APP_ID"),
            private_key=os.getenv("GITHUB_APP_PRIVATE_KEY2")
        )
        self.installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
        self._token = None
        self._token_expires_at = None

    async def get_token(self) -> str:
        """Get a valid installation token, refreshing if necessary"""
        if not self._token or not self._token_expires_at or datetime.now(UTC) >= self._token_expires_at:
            self._token = await self.app.get_installation_token(self.installation_id)
            self._token_expires_at = datetime.now(UTC) + timedelta(minutes=55)  # Tokens expire after 1 hour
        return self._token
