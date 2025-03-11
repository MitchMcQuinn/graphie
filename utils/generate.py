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
            - type: Optional generation type ('answer' or 'followup')
            - system: System prompt
            - user: User message to respond to
            - temperature: Optional temperature setting (default 0.7)
            - model: Optional model name (default gpt-4)
            - include_history: Optional flag to include chat history (default True)
    
    Returns:
        The generated text
    """
    logger.info(f"Generate function received input_data: {input_data}")
    
    # Determine generation type (answer or followup)
    generation_type = input_data.get('type', 'answer')
    
    # Extract common parameters with defaults
    system_prompt = input_data.get('system', 'You are a helpful assistant.')
    user_message = input_data.get('user', '')
    temperature = float(input_data.get('temperature', 0.5))
    model = input_data.get('model', 'gpt-4-turbo')
    include_history = input_data.get('include_history', True)
    
    logger.info(f"Generation type: {generation_type}, User message: '{user_message}', Model: {model}, Temperature: {temperature}")
    
    # If this is a followup generation, perform special processing
    if generation_type == 'followup':
        # Extract the main topic from the conversation history if possible
        main_topic = input_data.get('topic', 'the topic')
        
        # Try to detect the main topic from the first user message
        if 'chat_history' in session and len(session['chat_history']) > 0:
            for message in session['chat_history']:
                if message['role'] == 'user':
                    # This is likely the main topic - often a single word or short phrase
                    main_topic = message['content'].strip()
                    # If it's a long message, try to extract main topic words
                    if len(main_topic) > 30:
                        # Just take the first few words as the topic
                        words = main_topic.split()
                        if len(words) > 3:
                            main_topic = ' '.join(words[:3])
                    break
        
        # Build the context for the follow-up generation
        example_questions = [
            f"Would you like to know more about {main_topic}?",
            f"Is there a specific aspect of {main_topic} you'd like to learn more about?",
            f"Would you like me to explain how {main_topic} works in more detail?",
            f"Are you interested in learning about any other aspects of {main_topic}?",
            f"Is there anything else you'd like to know about {main_topic}?",
        ]
        
        # Use chat history to construct context if available
        context = "Generate a user-friendly follow-up question about the topic of conversation."
        
        if 'chat_history' in session and len(session['chat_history']) >= 2:
            # Extract the latest exchange
            recent_exchanges = []
            for i in range(min(4, len(session['chat_history']))):
                if i < len(session['chat_history']):
                    message = session['chat_history'][i]
                    recent_exchanges.append(f"{message['role'].capitalize()}: {message['content']}")
            
            if recent_exchanges:
                context = "Recent conversation:\n" + "\n".join(recent_exchanges)
        
        # Override the user_message with special followup format
        user_message = f'''{context}

The main topic appears to be: {main_topic}

Please generate a user-friendly follow-up question that:
1. Offers to provide more information about {main_topic}
2. Is conversational and accessible to someone who doesn't know much about the topic
3. Does NOT ask the user to provide technical information

Examples of good follow-up questions:
- {example_questions[0]}
- {example_questions[1]}
- {example_questions[2]}

Your follow-up question:'''
    
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
        if generation_type == 'followup':
            session['generation'] = f"Would you like to know more about {main_topic}?"
        else:
            session['generation'] = "I couldn't generate a response because the OpenAI API key is missing."
        return session['generation']
    
    # Get the OpenAI client
    client = get_openai_client()
    if not client:
        error_message = "Failed to initialize OpenAI client"
        logger.error(error_message)
        session['error'] = error_message
        if generation_type == 'followup':
            session['generation'] = "Is there anything else you'd like to know?"
        else:
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
        
        # For followup questions, clean up the text
        if generation_type == 'followup':
            # Clean up the text - strip any quotes or prefixes the model might add
            generated_text = generated_text.strip('"\'')
            if generated_text.lower().startswith("follow-up question:"):
                generated_text = generated_text[len("follow-up question:"):].strip()
        
        logger.info(f"Generated text: {generated_text[:100]}..." if len(generated_text) > 100 else f"Generated text: {generated_text}")
        
        # Store the result in the session for later reference
        session['generation'] = generated_text
        logger.info("Generation stored in session")
        
        return generated_text
    
    except Exception as e:
        error_message = f"Error generating response: {str(e)}"
        logger.error(f"OpenAI API error: {error_message}")
        session['error'] = error_message
        
        # Set a fallback generation message
        if generation_type == 'followup':
            # Provide a simple default follow-up
            if 'main_topic' in locals():
                default_question = f"Would you like to know more about {main_topic}?"
            else:
                default_question = "Is there anything else you'd like to know?"
            session['generation'] = default_question
            return default_question
        else:
            session['generation'] = "I'm sorry, I encountered an error while generating a response. Please check the API key or try again."
            return session['generation']

# Keep the generate_followup function as a wrapper for backward compatibility
def generate_followup(session, input_data):
    """
    Generate a contextual follow-up question that maintains the conversation topic.
    This is now a wrapper around the main generate function for backward compatibility.
    
    Args:
        session: The current session object to store results
        input_data: Dict containing parameters
    
    Returns:
        A follow-up question that maintains the conversation context
    """
    logger.info("Using legacy generate_followup function, now redirecting to unified generate function")
    
    # Add the type parameter for the main generate function
    input_data['type'] = 'followup'
    
    # Call the main generate function
    return generate(session, input_data)
