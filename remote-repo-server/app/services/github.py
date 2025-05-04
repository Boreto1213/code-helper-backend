from datetime import datetime, timedelta, UTC
import jwt
import httpx
from dotenv import load_dotenv
import os
from typing import List
from app.models.github import Comment

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

    async def create_github_review(self, pr_url: str, comments: List[Comment]):
        """Create GitHub review with comments and suggestions"""
        # Get fresh installation token
        token = await self.get_token()
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Code-Helper-App"
        }
        
        # Only proceed if we have comments
        if not comments:
            print("No comments parsed from the review")
            return
        
        # First, fetch the PR diff to get the line positions
        async with httpx.AsyncClient() as client:
            try:
                # Get PR details to get the diff URL
                pr_response = await client.get(
                    pr_url,
                    headers=headers
                )
                if pr_response.status_code != 200:
                    print(f"Error fetching PR details: {pr_response.text}")
                    return
                    
                pr_data = pr_response.json()
                
                # Extract owner, repo, and PR number from the PR URL
                # Example URL: https://api.github.com/repos/owner/repo/pulls/123
                pr_parts = pr_url.split('/')
                owner = pr_parts[-4]
                repo = pr_parts[-3]
                pr_number = pr_parts[-1]
                
                # Construct the correct diff URL
                diff_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
                
                # Get the diff content
                diff_response = await client.get(
                    diff_url,
                    headers=headers
                )
                if diff_response.status_code != 200:
                    print(f"Error fetching diff: {diff_response.text}")
                    return
                    
                diff_data = diff_response.json()
                
                # Create review data with line comments
                review_data = {
                    "body": "Code review by DeepSeek AI",
                    "event": "COMMENT",
                    "comments": []
                }
                
                # Process each comment and find its position in the diff
                for comment in comments:
                    # Find the file in the diff
                    file_found = False
                    for file_data in diff_data:
                        # Remove any square brackets from the file path
                        comment_file = comment.file.strip('[]')
                        if file_data['filename'] == comment_file:
                            file_found = True
                            # Get the patch content
                            patch = file_data.get('patch', '')
                            if not patch:
                                continue
                                
                            # Find the line in the patch
                            patch_lines = patch.split('\n')
                            line_found = False
                            position = 0
                            current_line = 0
                            
                            for i, line in enumerate(patch_lines):
                                if line.startswith('@@'):
                                    # Extract line numbers from diff hunk header
                                    try:
                                        # Format: @@ -old_start,old_lines +new_start,new_lines @@
                                        hunk_info = line.split('@@')[1].strip()
                                        new_start = int(hunk_info.split('+')[1].split(',')[0])
                                        current_line = new_start
                                    except (IndexError, ValueError):
                                        continue
                                elif line.startswith('+'):
                                    current_line += 1
                                    if current_line == comment.line:
                                        position = i
                                        line_found = True
                                        break
                                elif not line.startswith('-'):
                                    current_line += 1
                            
                            if line_found:
                                review_data["comments"].append({
                                    "path": comment_file,
                                    "position": position,
                                    "body": f"{comment.message}\n\n" + (f"```suggestion\n{comment.suggestion}\n```" if comment.suggestion else "")
                                })
                            else:
                                print(f"Warning: Could not find line {comment.line} in file {comment_file}")
                            break
                    
                    if not file_found:
                        print(f"Warning: Could not find file {comment_file} in the diff")
                
                # Only create the review if we have valid comments
                if review_data["comments"]:
                    # Create the review with line comments
                    response = await client.post(
                        f"{pr_url}/reviews",
                        headers=headers,
                        json=review_data
                    )
                    
                    if response.status_code == 201:
                        print(f"Successfully created review with {len(review_data['comments'])} line comments")
                    else:
                        print(f"Error creating review: {response.text}")
                else:
                    print("No valid comments to create review with")
                    
            except Exception as e:
                print(f"Request failed: {str(e)}")
                raise