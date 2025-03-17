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
from utils.resolve_variable import process_variables
import openai
import time
from openai import OpenAI

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
        session: The current session object to store results (legacy support)
        input_data: Dict containing:
            - system: System prompt
            - user: User message to respond to
            - temperature: Optional temperature setting (default 0.7)
            - model: Optional model name (default gpt-4)
            - include_history: Optional flag to include chat history (default True)
            - schema: JSON schema defining the structure of the output (optional)
            - schema_description: Description of the schema for the AI (optional)
            - directly_set_reply: Whether to directly update session.reply (default False)
    
    Returns:
        The generated structured response as a Python dictionary
    """
    logger.info(f"Generate function received input_data: {input_data}")
    
    # Process variables in input_data if using new architecture
    if 'id' in session:
        try:
            from engine import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver:
                # Handle SESSION_ID special variable in user message
                if 'user' in input_data and isinstance(input_data['user'], str):
                    # First, handle direct SESSION_ID replacement (not in @{} format)
                    if 'SESSION_ID' in input_data['user']:
                        input_data['user'] = input_data['user'].replace('SESSION_ID', session['id'])
                    
                    # Then, handle special variable format with direct access
                    if input_data['user'].startswith('@{') and '.get-question.response' in input_data['user']:
                        # Directly get the user's response from memory
                        try:
                            with driver.session() as db_session:
                                result = db_session.run("""
                                    MATCH (s:SESSION {id: $session_id})
                                    RETURN s.memory as memory
                                """, session_id=session['id'])
                                
                                record = result.single()
                                if record and record['memory']:
                                    memory = json.loads(record['memory'])
                                    # Look for response in response-get-question or get-question
                                    response = None
                                    if 'response-get-question' in memory and memory['response-get-question']:
                                        response_objects = memory['response-get-question']
                                        if response_objects and 'response' in response_objects[-1]:
                                            response = response_objects[-1]['response']
                                    
                                    if not response and 'get-question' in memory and memory['get-question']:
                                        for output in reversed(memory['get-question']):
                                            if 'response' in output and output['response'] != 'GM! How can I help you today?':
                                                response = output['response']
                                                break
                                    
                                    if response:
                                        input_data['user'] = response
                                        logger.info(f"Resolved get-question.response to: {response}")
                        except Exception as e:
                            logger.error(f"Error resolving get-question response: {str(e)}")
                
                # Use the new variable resolution for other variables
                input_data = process_variables(driver, session['id'], input_data)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Error processing variables: {str(e)}")
            # Fall back to legacy resolution
            pass
    
    # Extract parameters with defaults
    system_prompt = input_data.get('system', 'You are a helpful assistant.')
    user_message = input_data.get('user', '')
    temperature = float(input_data.get('temperature', 0.7))
    model = input_data.get('model', 'gpt-4-turbo')
    include_history = input_data.get('include_history', True)
    directly_set_reply = input_data.get('directly_set_reply', False)
    
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
    schema_description = input_data.get('schema_description', None)
    if not schema_description:
        schema_description = "Respond in a JSON format with the following structure"
    
    # Extract chat history if we need to include it
    messages = []
    
    # Always add the system message first
    messages.append({"role": "system", "content": system_prompt})
    
    # Add history if requested
    if include_history and 'id' in session:
        try:
            from engine import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver:
                with driver.session() as db_session:
                    # Get chat history from SESSION node
                    result = db_session.run("""
                        MATCH (s:SESSION {id: $session_id})
                        RETURN s.chat_history as chat_history
                    """, session_id=session['id'])
                    
                    record = result.single()
                    if record and record['chat_history']:
                        # Parse chat history
                        try:
                            chat_history = json.loads(record['chat_history'])
                            for message in chat_history:
                                if 'role' in message and 'content' in message:
                                    messages.append(message)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid chat history JSON for session {session['id']}")
        except (ImportError, Exception) as e:
            logger.warning(f"Error including chat history: {str(e)}")
    
    # Add the user message with schema information
    if schema:
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
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            
            try:
                result = json.loads(response_text)
                
                # Store the result if using Neo4j
                if 'id' in session:
                    try:
                        from engine import get_neo4j_driver
                        driver = get_neo4j_driver()
                        if driver:
                            # Store the result in session memory
                            step_id = input_data.get('step_id', 'generate')
                            store_memory(driver, session['id'], step_id, result)
                            
                            # Directly update session reply if requested
                            if directly_set_reply and 'response' in result:
                                with driver.session() as db_session:
                                    db_session.run("""
                                        MATCH (s:SESSION {id: $session_id})
                                        SET s.reply = $reply
                                    """, session_id=session['id'], reply=result['response'])
                                    
                                    # Add the reply to chat history
                                    db_session.run("""
                                        MATCH (s:SESSION {id: $session_id})
                                        WITH s, 
                                             CASE 
                                                WHEN s.chat_history IS NULL THEN '[]' 
                                                ELSE s.chat_history 
                                             END as existing_history
                                        SET s.chat_history = 
                                            CASE 
                                                WHEN existing_history = '[]' THEN '[{"role": "assistant", "content": "' + $reply + '"}]'
                                                ELSE SUBSTRING(existing_history, 0, SIZE(existing_history) - 1) + ', {"role": "assistant", "content": "' + $reply + '"}]'
                                            END
                                    """, session_id=session['id'], reply=result['response'].replace('"', '\\"').replace('\n', '\\n'))
                    except (ImportError, Exception) as e:
                        logger.warning(f"Error storing result in Neo4j: {str(e)}")
                
                return result
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response: {response_text}")
                # If we can't parse JSON, return a simple response
                result = {"response": response_text}
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
