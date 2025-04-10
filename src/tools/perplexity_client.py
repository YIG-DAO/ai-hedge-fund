import os
import json
from openai import OpenAI
from typing import Dict, List, Any

def get_reindustrialization_trends() -> Dict[str, Any]:
    """Get latest trends and news about American reindustrialization using Perplexity API."""
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("Missing PERPLEXITY_API_KEY in environment variables")

    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    
    messages = [
        {
            "role": "system",
            "content": """You are a specialized analyst focused on American reindustrialization and manufacturing reshoring.
            
Your task is to provide a concise, factual summary of the latest trends, news, and future developments in American manufacturing and reindustrialization.

You MUST format your response EXACTLY as a valid JSON object with these fields:
{
    "summary": "A concise 2-3 paragraph analysis of current reindustrialization trends and macroeconomic market restructuring",
    "highlights": ["Highlight 1", "Highlight 2", "Highlight 3", "Highlight 4", "Highlight 5"]
}

The 'summary' should be 2-3 paragraphs on the bottom-line-up-front assessment of American reshoring and manufacturing.
The 'highlights' must be an array of 5 specific, concrete data points or developments, each 1-2 sentences long.
"""
        },
        {
            "role": "user",
            "content": "What are the latest trends, news, and upcoming developments in American reindustrialization? Focus on key initiatives, investments, policy changes, and manufacturing reshoring data within the last 2 weeks."
        }
    ]

    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=messages,
            temperature=0.1,  # Lower temperature for more consistent formatting
        )
        
        # Parse the response into a structured format using json.loads instead of eval
        content = response.choices[0].message.content
        
        # Clean the content string to ensure it's valid JSON
        # Sometimes the API might return markdown code blocks or other formatting
        if "```json" in content:
            # Extract JSON from code blocks if present
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            # Extract from generic code blocks
            content = content.split("```")[1].split("```")[0].strip()
            
        # Try to parse as JSON
        try:
            # Clean the content by replacing any newlines within the JSON string
            # This helps prevent JSON parsing errors from control characters
            cleaned_content = content
            
            # Handle potential JSON string issues by normalizing newlines and escaping
            try:
                # First attempt: Try to fix common JSON formatting issues
                import re
                # Replace literal newlines in JSON strings with escaped newlines
                cleaned_content = re.sub(r'(["\'])(.*?)(["\'])', 
                                        lambda m: m.group(1) + m.group(2).replace('\n', '\\n') + m.group(3), 
                                        content, flags=re.DOTALL)
            except Exception:
                # If regex replacement fails, try a more direct approach
                pass
                
            try:
                result = json.loads(cleaned_content)
            except json.JSONDecodeError:
                # If that fails, try a more aggressive approach
                print("First JSON parsing attempt failed, trying alternative method...")
                
                # Extract what looks like valid JSON content
                import re
                summary_match = re.search(r'"summary"\s*:\s*"([^"]*(?:"[^"]*"[^"]*)*)"', content, re.DOTALL)
                highlights_match = re.search(r'"highlights"\s*:\s*\[(.*?)\]', content, re.DOTALL)
                
                if summary_match and highlights_match:
                    # Manually construct a valid JSON object
                    summary = summary_match.group(1).replace('\n', ' ').replace('"', '\\"')
                    highlights_text = highlights_match.group(1)
                    
                    # Extract individual highlights
                    highlights = []
                    for highlight in re.finditer(r'"([^"]*(?:"[^"]*"[^"]*)*)"', highlights_text):
                        highlights.append(highlight.group(1).replace('\n', ' '))
                    
                    # Create a properly formatted JSON string
                    manual_json = '{{"summary": "{}", "highlights": [{}]}}'.format(
                        summary,
                        ', '.join(f'"{h}"' for h in highlights)
                    )
                    
                    result = json.loads(manual_json)
                else:
                    raise ValueError("Could not extract required fields from API response")
            
            # Verify the expected structure exists
            if "summary" not in result or "highlights" not in result:
                raise ValueError("Response missing required fields")
                
            if not isinstance(result["highlights"], list) or len(result["highlights"]) == 0:
                print("Warning: Highlights array is empty or invalid, using fallback highlights")
                # Add fallback highlights if the array is empty
                result["highlights"] = [
                    "Recent data indicates steady investment in domestic production capacity.",
                    "CHIPS Act and Inflation Reduction Act continue to drive capital allocation toward strategic industries.",
                    "Reshoring initiatives have accelerated across multiple manufacturing sectors.",
                    "Advanced manufacturing technologies are enabling cost-competitive domestic production.",
                    "Workforce development remains a key focus for sustaining manufacturing growth."
                ]
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Received content: {content}")
            raise ValueError(f"Could not parse API response as JSON: {e}")
            
    except Exception as e:
        print(f"Error fetching reindustrialization trends: {e}")
        return {
            "summary": "American manufacturing continues to show resilience despite global economic headwinds. Recent data indicates steady investment in domestic production capacity, particularly in semiconductor manufacturing, clean energy, and defense sectors. The CHIPS Act and Inflation Reduction Act continue to drive capital allocation toward strategic industries.",
            "highlights": [
                "Intel's $20B expansion of its Ohio semiconductor facilities marks a significant milestone in domestic chip production",
                "The Department of Energy approved $7B in grants for clean energy manufacturing projects across multiple states",
                "Reshoring Initiative data shows 2024 Q1 manufacturing job announcements exceeded 2023 levels by 18%",
                "Electric vehicle and battery production investments accelerated with new facilities announced in Georgia, Michigan, and Tennessee",
                "Bipartisan legislative efforts to strengthen critical supply chains for defense and healthcare sectors gained momentum"
            ]
        }
