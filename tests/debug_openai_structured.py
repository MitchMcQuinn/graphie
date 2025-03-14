#!/usr/bin/env python
import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')
api_key = os.getenv('OPENAI_API_KEY')

def test_structured_output():
    """Test structured output directly with OpenAI API"""
    client = OpenAI(api_key=api_key)
    
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of a famous person"},
            "birth_year": {"type": "integer", "description": "Year they were born"}
        },
        "required": ["name", "birth_year"]
    }
    
    # First approach - using response_format with type and schema
    try:
        logger.info("Approach 1: Using response_format with type and schema")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me about Albert Einstein"}
            ],
            response_format={"type": "json_object", "schema": schema}
        )
        logger.info(f"APPROACH 1 RESPONSE: {response.choices[0].message.content}")
    except Exception as e:
        logger.error(f"Approach 1 failed: {str(e)}")
    
    # Second approach - using just json_object
    try:
        logger.info("Approach 2: Using just json_object type")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me about Albert Einstein"}
            ],
            response_format={"type": "json_object"}
        )
        logger.info(f"APPROACH 2 RESPONSE: {response.choices[0].message.content}")
    except Exception as e:
        logger.error(f"Approach 2 failed: {str(e)}")
    
    # Third approach - using different structure
    try:
        logger.info("Approach 3: Using function-style approach")
        tool_schema = {
            "name": "get_person_info",
            "description": "Get information about a person",
            "parameters": schema
        }
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me about Albert Einstein"}
            ],
            tools=[{"type": "function", "function": tool_schema}],
            tool_choice={"type": "function", "function": {"name": "get_person_info"}}
        )
        logger.info(f"APPROACH 3 RESPONSE: {response.choices[0].message.tool_calls[0].function.arguments}")
    except Exception as e:
        logger.error(f"Approach 3 failed: {str(e)}")

    # Fourth approach - check which models support structured outputs
    try:
        logger.info("Approach 4: Using a different model")
        response = client.chat.completions.create(
            model="gpt-4o",  # Try with a different model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me about Albert Einstein"}
            ],
            response_format={"type": "json_object"}
        )
        logger.info(f"APPROACH 4 RESPONSE: {response.choices[0].message.content}")
    except Exception as e:
        logger.error(f"Approach 4 failed: {str(e)}")
        
if __name__ == "__main__":
    test_structured_output() 