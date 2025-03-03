import os
from openai import OpenAI
from typing import Dict

def get_reindustrialization_trends() -> Dict[str, str]:
    """Get latest trends and news about American reindustrialization using Perplexity API."""
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("Missing PERPLEXITY_API_KEY in environment variables")

    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    
    messages = [
        {
            "role": "system",
            "content": "You are a specialized analyst focused on American reindustrialization. Provide a concise, factual summary of the latest trends, news, and future developments. Format the response as a dictionary with 'summary' and 'highlights' keys."
        },
        {
            "role": "user",
            "content": "What are the latest trends, news, and upcoming developments in American reindustrialization? Focus on key initiatives, investments, and policy changes within the last month."
        }
    ]

    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=messages,
        )
        
        # Parse the response into a structured format
        content = response.choices[0].message.content
        # The API should return a dictionary-like string that we can eval
        result = eval(content)
        return result
    except Exception as e:
        print(f"Error fetching reindustrialization trends: {e}")
        return {
            "summary": "Error fetching reindustrialization trends",
            "highlights": ["Data temporarily unavailable"]
        }
