import os
import logging
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Store the API key
api_key = os.getenv('OPENAI_API_KEY')

# Define a function that will lazily initialize the client when needed
# This avoids initialization errors at import time
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
            - agent: Optional agent name/role
            - user: User message to respond to
            - temperature: Optional temperature setting (default 0.7)
            - model: Optional model name (default gpt-4)
    
    Returns:
        The generated text
    """
    logger.info(f"Generate function received input_data: {input_data}")
    
    system_prompt = input_data.get('system', 'You are a helpful assistant.')
    user_message = input_data.get('user', '')
    temperature = float(input_data.get('temperature', 0.7))
    model = input_data.get('model', 'gpt-4')
    
    logger.info(f"User message: '{user_message}', Model: {model}, Temperature: {temperature}")
    
    # Prepare the messages for the API call
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # If agent is provided, add it to the system prompt
    if 'agent' in input_data:
        messages[0]["content"] += f"\nYou are {input_data['agent']}."
    
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
        # Set a fallback generation message
        session['generation'] = "I'm sorry, I encountered an error while generating a response. Please check the API key or try again."
        return session['generation']
