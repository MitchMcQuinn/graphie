"""
utils/generate.py
----------------
This module handles OpenAI API integration for text generation.

Purpose:
    Provides utilities to initialize an OpenAI client and generate content
    using OpenAI's API services.

Functionality:
    - Loads environment variables from .env.local
    - Configures the OpenAI client with appropriate settings
    - Handles generation requests through the OpenAI API
    - Includes error handling and logging
"""

import os
import logging
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Store the API key
api_key = os.getenv('OPENAI_API_KEY')

def get_openai_client():
    try:
        import httpx
        from openai import OpenAI
        
        # Create a transport with no proxies
        transport = httpx.HTTPTransport(proxy=None)
        http_client = httpx.Client(transport=transport)
        
        # Create the client with our custom HTTP client
        client = OpenAI(api_key=api_key, http_client=http_client)
        logger.info("Successfully created OpenAI client")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        return None

def generate(session, input_data):
    """
    Generate a response using OpenAI API
    
    Args:
        session: The current session object to store results
        input_data: Dict containing:
            - system: System prompt
            - user: User message to respond to
            - temperature: Optional temperature setting (default 0.7)
            - model: Optional model name (default gpt-4)
            - include_history: Optional flag to include chat history (default True)
    
    Returns:
        The generated text
    """
    logger.info(f"Generate function received input_data: {input_data}")
    
    # Extract parameters with defaults
    system_prompt = input_data.get('system', 'You are a helpful assistant.')
    user_message = input_data.get('user', '')
    temperature = float(input_data.get('temperature', 0.7))
    model = input_data.get('model', 'gpt-4-turbo')
    include_history = input_data.get('include_history', True)
    
    logger.info(f"User message: '{user_message}', Model: {model}, Temperature: {temperature}")
    
    # Prepare the messages for the API call
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # If agent is provided, add it to the system prompt
    if 'agent' in input_data:
        messages[0]["content"] += f"\nYou are {input_data['agent']}."
    
    # If include_history is true and chat history exists, include relevant history
    # to maintain context across conversation loops
    if include_history and 'chat_history' in session and len(session['chat_history']) > 0:
        # Get the last 4-6 messages (or all if fewer) to provide context
        # Skip adding the last message since it will be added explicitly
        history_to_include = session['chat_history'][:-1]
        if len(history_to_include) > 6:
            # If there's a lot of history, only include the most recent messages
            history_to_include = history_to_include[-6:]
            
        for message in history_to_include:
            messages.append({"role": message['role'], "content": message['content']})
        
        logger.info(f"Including {len(history_to_include)} messages from chat history for context")
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    logger.info(f"API messages: {messages}")
    
    # Check if API key is present
    if not api_key:
        error_message = "OpenAI API key is missing. Please set OPENAI_API_KEY in .env.local"
        logger.error(error_message)
        session['error'] = error_message
        session['generation'] = "I couldn't generate a response because the OpenAI API key is missing."
        return session['generation']
    
    # Get the OpenAI client
    client = get_openai_client()
    if not client:
        error_message = "Failed to initialize OpenAI client"
        logger.error(error_message)
        session['error'] = error_message
        session['generation'] = "I'm sorry, I encountered an error while connecting to the AI service."
        return session['generation']
    
    try:
        # Make the API call - updated to use the client
        logger.info(f"Making API call to model: {model}")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        
        # Extract the generated text
        generated_text = response.choices[0].message.content
        
        logger.info(f"Generated text: {generated_text[:100]}..." if len(generated_text) > 100 else f"Generated text: {generated_text}")
        
        # Store the result in the session for later reference
        session['generation'] = generated_text
        logger.info("Generation stored in session")
        
        return generated_text
    
    except Exception as e:
        error_message = f"Error generating response: {str(e)}"
        logger.error(f"OpenAI API error: {error_message}")
        session['error'] = error_message
        session['generation'] = "I'm sorry, I encountered an error while generating a response. Please check the API key or try again."
        return session['generation']
