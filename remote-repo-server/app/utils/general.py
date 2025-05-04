from typing import List
import re
from app.models.github import Comment

def parse_review_comments(review_text: str) -> List[Comment]:
    comments = []
    current_file = None
    current_line = None
    
    # Updated regex patterns to handle the AI's format
    file_pattern = r'([^:]+):(\d+)(?:-(\d+))?'
    suggestion_pattern = r'```suggestion\n(.*?)```'
    
    lines = review_text.split('\n')
    current_message = []
    current_suggestion = None
    
    for i, line in enumerate(lines):
        # Check for file and line reference
        file_match = re.search(file_pattern, line)
        if file_match:
            # Save previous comment if exists
            if current_file and current_message:
                comments.append(Comment(
                    current_file,
                    current_line,
                    '\n'.join(current_message).strip(),
                    current_suggestion
                ))
            
            # Handle both formats: file.ext:line and file.ext:start-end
            current_file = file_match.group(1).strip()
            current_line = int(file_match.group(2))
            
            current_message = []
            current_suggestion = None
            continue
        
        # Check for code suggestion
        if '```suggestion' in line:
            # Get all lines until the closing ```
            suggestion_lines = []
            j = i + 1
            while j < len(lines) and '```' not in lines[j]:
                suggestion_lines.append(lines[j])
                j += 1
            current_suggestion = '\n'.join(suggestion_lines).strip()
            continue
        
        # Skip suggestion blocks
        if '```' in line:
            continue
            
        # Add line to current message if we have a file context
        if current_file and line.strip():
            current_message.append(line)
    
    # Add the last comment
    if current_file and current_message:
        comments.append(Comment(
            current_file,
            current_line,
            '\n'.join(current_message).strip(),
            current_suggestion
        ))
    
    # Debug output
    print("\nParsed Comments:")
    for comment in comments:
        print(f"\nFile: {comment.file}, Line: {comment.line}")
        print(f"Message: {comment.message}")
        if comment.suggestion:
            print(f"Suggestion: {comment.suggestion}")
    
    return comments