"""
utils/generate.py
----------------
This module handles OpenAI API integration for text generation with structured outputs.

Purpose:
    Provides utilities to initialize an OpenAI client and generate structured content
    using OpenAI's API services.

Functionality:
    - Loads environment variables from .env.local
    - Configures the OpenAI client with appropriate settings
    - Handles generation requests through the OpenAI API
    - Returns structured JSON outputs
    - Includes error handling and logging
"""

import os
import logging
import json
from dotenv import load_dotenv
from utils.store_memory import store_memory
from utils.session_manager import get_session_manager
from utils.resolve_variable import process_variables
from openai import OpenAI
import time

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Store the API key
api_key = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

def generate(session, input_data):
    """
    Generate a structured response using OpenAI API
    
    Args:
        session: Session object containing id and metadata
        input_data: Dict containing:
            - system: System prompt
            - user: User message to respond to
            - temperature: Optional temperature setting (default 0.7)
            - model: Optional model name (default gpt-4-turbo)
            - include_history: Optional flag to include chat history (default True)
            - schema: JSON schema defining the structure of the output (optional)
            - schema_description: Description of the schema for the AI (optional)
            - directly_set_reply: Whether to directly update session.reply (default False)
            - step_id: Optional step_id to use when storing the result
            - response_key: Optional key to use for simplified response format (optional)
    
    Returns:
        The generated structured response as a Python dictionary
    """
    logger.info(f"Generate function received input_data: {input_data}")
    
    # Get Neo4j driver
    from engine import get_neo4j_driver
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Neo4j driver not available")
        return {"response": "Error: Neo4j connection unavailable"}
    
    # Get the session manager
    session_manager = get_session_manager(driver)
    if not session_manager:
        logger.error("Session manager not available")
        return {"response": "Error: Session manager unavailable"}
    
    # Get the session ID
    session_id = session['id']
    
    # Handle direct SESSION_ID replacement in user message
    if 'user' in input_data and isinstance(input_data['user'], str):
        # Check if it contains a variable reference
        if '@{' in input_data['user']:
            input_data['user'] = process_variables(driver, session_id, input_data['user'])
        # Check direct SESSION_ID replacement
        elif 'SESSION_ID' in input_data['user']:
            input_data['user'] = input_data['user'].replace('SESSION_ID', session_id)
    
    # Process other variables in input_data
    input_data = process_variables(driver, session_id, input_data)
    
    # Extract parameters with defaults
    system_prompt = input_data.get('system', 'You are a helpful assistant.')
    user_message = input_data.get('user', '')
    temperature = float(input_data.get('temperature', 0.7))
    model = input_data.get('model', 'gpt-4-turbo')
    include_history = input_data.get('include_history', True)
    directly_set_reply = input_data.get('directly_set_reply', False)
    step_id = input_data.get('step_id', 'generate')
    response_key = input_data.get('response_key', None)  # New parameter for simplified output
    
    logger.info(f"User message: '{user_message}', Model: {model}, Temperature: {temperature}")
    
    # Get schema if provided, or use a simple default schema
    schema = input_data.get('schema', {
        "type": "object",
        "properties": {
            "response": {
                "type": "string",
                "description": "The response to the user's query"
            }
        },
        "required": ["response"]
    })
    
    # Get the schema description if provided, or generate one
    schema_description = input_data.get('schema_description', 
                                       "Respond in a JSON format with the following structure")
    
    # Extract chat history if we need to include it
    messages = []
    
    # Always add the system message first
    messages.append({"role": "system", "content": system_prompt})
    
    # Add history if requested
    if include_history:
        chat_history = session_manager.get_chat_history(session_id)
        for message in chat_history:
            if 'role' in message and 'content' in message:
                messages.append(message)
    
    # Add the user message with schema information
    if schema and not response_key:
        # Format the schema as a pretty string
        schema_str = json.dumps(schema, indent=2)
        user_content = f"{user_message}\n\n{schema_description}:\n{schema_str}"
    else:
        user_content = user_message
    
    messages.append({"role": "user", "content": user_content})
    
    # Call OpenAI API
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"} if not response_key else None
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            
            # Handle the response based on how we want to process it
            if response_key:
                # Simplified response handling - just store the response text in the specified key
                result = {response_key: response_text}
                logger.info(f"Using simple response format with key '{response_key}'")
            else:
                # Standard JSON parsing
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON response: {response_text}")
                    # If we can't parse JSON, return a simple response
                    result = {"response": response_text}
            
            # Store the result in session memory
            session_manager.store_memory(session_id, step_id, result)
            
            # Directly update session reply if requested
            if directly_set_reply:
                reply_text = result.get(response_key or 'response', response_text)
                session_manager.add_assistant_message(session_id, reply_text)
            
            return result
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"OpenAI API error (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
            else:
                logger.error(f"OpenAI API error after {max_retries} attempts: {str(e)}")
                raise
    
    # If we reached here, all retry attempts failed
    return {"response": "I'm sorry, I encountered an error processing your request."}
