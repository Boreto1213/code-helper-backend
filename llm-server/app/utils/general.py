def create_pr_review_prompt(pr_info: dict, changes: dict) -> str:
    """Create a structured prompt that will generate parseable responses"""
    # First, create a list of valid line numbers for each file
    file_line_numbers = {}
    for file in changes['changed_files']:
        if file['patch']:
            lines = []
            current_line = None
            for line in file['patch'].split('\n'):
                if line.startswith('@@'):
                    # Extract the line number from the patch header
                    try:
                        current_line = int(line.split(',')[0].split('@@')[1].strip().split(' ')[0])
                    except (IndexError, ValueError):
                        continue
                elif line.startswith('+') or line.startswith('-'):
                    if current_line is not None:
                        lines.append(current_line)
                        current_line += 1
            file_line_numbers[file['filename']] = sorted(set(lines))
    
    # Create a summary of available line numbers for each file
    line_number_summary = "\n".join([
        f"File: {filename}\nAvailable line numbers: {', '.join(map(str, lines))}"
        for filename, lines in file_line_numbers.items()
    ])
    
    files_with_changes = "\n".join([
        f"File: {f['filename']}\nChanges:\n{f['patch']}\n"
        for f in changes['changed_files'] if f['patch']
    ])
    
    prompt = f"""Please review this pull request and provide specific comments in the following format:

For each issue or suggestion, use this structure:
[filename.ext]:<line_number>
Your comment about the code
```suggestion
Your suggested code change (if applicable)
```

CRITICAL INSTRUCTIONS:
1. You MUST use EXACT line numbers from the provided diff only. Here are the available line numbers for each file:
{line_number_summary}

2. DO NOT comment on line 1 of any file unless it is explicitly shown in the diff with a + or - prefix.

3. Only comment on lines that are shown in the diff with + or - prefixes.

4. The line numbers in your comments MUST match exactly with the line numbers shown in the diff.

5. If you want to comment on multiple lines, use a range like this: [filename.ext]:start-end
   For example: [main.py]:13-21
   The parser will automatically use the first line number (13 in this case).

For example, if you see this in the diff:
@@ -15,3 +15,4 @@
  def some_function():
      print("Hello")
+     print("World")  # This is on line 18
      return True

You can comment on line 18 like this:
[main.py]:18
Consider adding a docstring to explain the function's purpose
```suggestion
def some_function():
    Prints a greeting and returns True.
    print("Hello")
    print("World")
    return True
```

PR Details:
Title: {pr_info['title']}
Author: {pr_info['author']}
Branch: {pr_info['head_branch']} → {pr_info['base_branch']}

Changes to review:
{files_with_changes}

Please provide a detailed review focusing on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Specific suggestions for improvement

Remember: Your comments will be rejected if they reference line numbers that are not shown in the diff.
"""
    return prompt