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
    - Provides specialized structured generation
    - Formats analysis results
"""

import os
import logging
import json
from dotenv import load_dotenv
from core.store_memory import store_memory
from core.session_manager import get_session_manager
from core.resolve_variable import process_variables
from openai import OpenAI
import time
import httpx

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Store the API key
api_key = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client with correct configuration
http_client = httpx.Client(
    base_url="https://api.openai.com/v1",
    timeout=30.0
)

client = OpenAI(
    api_key=api_key,
    http_client=http_client
)

def _generate_api_response(session, input_data):
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
    from core.database import get_neo4j_driver
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

def generate(session, input_data):
    """
    Generate a structured analysis using OpenAI API, and store results in session
    for easier access.
    
    This is an enhanced version of _generate_api_response() that:
    1. Calls the standard generate function
    2. Extracts and processes the structured result
    3. Makes individual fields directly accessible in the session
    
    Args:
        session: The current session object
        input_data: Dict with parameters for generate._generate_api_response
    
    Returns:
        The generated structured response as a Python dictionary
    """
    logger.info(f"Analyze input function received input_data: {input_data}")
    
    # Call the standard generate function
    result = _generate_api_response(session, input_data)
    logger.info(f"Generate function returned: {result}")
    
    # The structured result should be in the session
    # Try to find it among several possible keys
    structured_result = None
    result_keys = ['structured_result', 'result', 'generation']
    
    for key in result_keys:
        if key in session:
            try:
                if isinstance(session[key], str):
                    # Try to parse it as JSON if it's a string
                    structured_result = json.loads(session[key])
                    logger.info(f"Found structured result in session[{key}] and parsed from JSON: {structured_result}")
                    break
                elif isinstance(session[key], dict):
                    structured_result = session[key]
                    logger.info(f"Found structured result in session[{key}] as dict: {structured_result}")
                    break
            except Exception as e:
                logger.error(f"Error processing session[{key}]: {e}")
                # Store the raw string if JSON parsing fails
                structured_result = session[key]
                logger.info(f"Storing raw string as structured_result: {structured_result}")
    
    # Always store the result, even if it's None
    session['structured_result'] = structured_result
    logger.info(f"Stored in session['structured_result']: {structured_result}")
    
    # If we found a structured result, extract its components
    if structured_result:
        if isinstance(structured_result, dict):
            # Store individual fields for easier access
            for key, value in structured_result.items():
                session[key] = value
                logger.info(f"Stored in session['{key}']: {value}")
        else:
            logger.error(f"Structured result is not a dict: {type(structured_result)}")
    else:
        logger.warning("Could not find structured result in session")
    
    # Log the final state of relevant session data
    logger.info("Final session data after generate:")
    for key in session:
        if key in result_keys or key == 'structured_result':
            logger.info(f"  - {key}: {session[key]}")
    
    return result

def format_analysis(session, input_data):
    """
    Format structured data from the session into a human-readable text format.
    
    This utility takes data fields and produces a formatted analysis text,
    storing both the formatted output and the individual fields.
    
    Args:
        session: The current session object
        input_data: Dict containing field names and values to format
    
    Returns:
        True to indicate success
    """
    logger.info(f"Format analysis function received input_data: {input_data}")
    
    # Format a simple text result from the available fields
    formatted_parts = ["Analysis results:"]
    
    # Process all input fields
    for key, value in input_data.items():
        # Convert string booleans to actual booleans if needed
        if isinstance(value, str) and value.lower() in ["true", "false"]:
            if value.lower() == "true":
                formatted_value = True
            else:
                formatted_value = False
        else:
            formatted_value = value
            
        # Add to formatted output
        formatted_parts.append(f"\n\n{key.replace('_', ' ').title()}: {formatted_value}")
        
        # Store in session with _formatted suffix
        session[f"{key}_formatted"] = formatted_value
        logger.info(f"Stored {key}_formatted in session: {formatted_value}")
    
    # Create the final formatted result
    formatted_result = "".join(formatted_parts)
    logger.info(f"Formatted result: {formatted_result}")
    
    # Store in session
    session['formatted_result'] = formatted_result
    
    # Log the final state
    logger.info("Final session data after format_analysis:")
    logger.info(f"  - formatted_result: {session['formatted_result']}")
    
    return True
