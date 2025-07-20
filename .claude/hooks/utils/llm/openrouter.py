#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv


def prompt_llm(prompt_text):
    """
    Base OpenRouter LLM prompting method using configurable model.
    
    Args:
        prompt_text (str): The prompt to send to the model
    
    Returns:
        str: The model's response text, or None if error
    """
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    
    # Get model from environment or use default
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
    
    # Warn about problematic models
    problematic_models = ["deepseek/"]
    for pm in problematic_models:
        if model.startswith(pm):
            print(f"Warning: Model '{model}' may output reasoning instead of direct answers", file=sys.stderr)
    
    try:
        # Prepare the request data
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        # Create the request
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://github.com/claude-code-hooks"),
                "X-Title": "Claude Code Hooks"
            }
        )
        
        # Send the request
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            # Debug print the result structure
            if os.getenv("DEBUG_OPENROUTER"):
                print(f"API Response: {json.dumps(result, indent=2)}", file=sys.stderr)
            
            # Extract content - handle potential variations in response format
            choice = result.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            # Try standard content field first
            content = message.get('content', '')
            
            # Some models like DeepSeek might use reasoning field
            if not content:
                content = message.get('reasoning', '')
            
            # Try text field as fallback
            if not content:
                content = choice.get('text', '')
            
            return content.strip() if content else None
    
    except urllib.error.HTTPError as e:
        # Try to get error details from response
        try:
            error_data = json.loads(e.read())
            error_msg = error_data.get('error', {}).get('message', str(e))
            print(f"OpenRouter API error: {error_msg}", file=sys.stderr)
            print(f"Status code: {e.code}", file=sys.stderr)
            print(f"Model used: {model}", file=sys.stderr)
        except:
            print(f"OpenRouter API HTTP error: {e}", file=sys.stderr)
            print(f"Status code: {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"OpenRouter API error: {e}", file=sys.stderr)
        print(f"Model used: {model}", file=sys.stderr)
        return None


def generate_completion_message():
    """
    Generate a completion message using OpenRouter LLM.
    
    Returns:
        str: A natural language completion message, or None if error
    """
    engineer_name = os.getenv("ENGINEER_NAME", "").strip()
    
    if engineer_name:
        name_instruction = f"Sometimes (about 30% of the time) include the engineer's name '{engineer_name}' in a natural way."
        examples = f"""Examples of the style: 
- Standard: "Work complete!", "All done!", "Task finished!", "Ready for your next move!"
- Personalized: "{engineer_name}, all set!", "Ready for you, {engineer_name}!", "Complete, {engineer_name}!", "{engineer_name}, we're done!" """
    else:
        name_instruction = ""
        examples = """Examples of the style: "Work complete!", "All done!", "Task finished!", "Ready for your next move!" """
    
    prompt = f"""Generate a short, concise, friendly completion message for when an AI coding assistant finishes a task. 

Requirements:
- Keep it under 10 words
- Make it positive and future focused
- Use natural, conversational language
- Focus on completion/readiness
- Do NOT include quotes, formatting, or explanations
- Return ONLY the completion message text
{name_instruction}

{examples}

Generate ONE completion message:"""
    
    response = prompt_llm(prompt)
    
    # Clean up response - remove quotes and extra formatting
    if response:
        response = response.strip().strip('"').strip("'").strip()
        # Take first line if multiple lines
        response = response.split("\n")[0].strip()
    
    return response


def main():
    """Command line interface for testing."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--completion":
            message = generate_completion_message()
            if message:
                print(message)
            else:
                print("Error generating completion message")
        else:
            prompt_text = " ".join(sys.argv[1:])
            response = prompt_llm(prompt_text)
            if response:
                print(response)
            else:
                print("Error calling OpenRouter API")
    else:
        print("Usage: ./openrouter.py 'your prompt here' or ./openrouter.py --completion")


if __name__ == "__main__":
    main()