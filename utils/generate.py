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
    - Supports structured output generation with JSON schemas
    - Implements rate limiting to avoid API throttling
"""

import os
import logging
import json
from dotenv import load_dotenv
from utils.rate_limiter import get_openai_limiter

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Store the API key
api_key = os.getenv('OPENAI_API_KEY')

def get_openai_client():
    try:
        # First, try to import the required modules
        try:
            import httpx
        except ImportError:
            logger.error("Missing dependency: 'httpx' package is not installed.")
            logger.error("Please install it with: pip install httpx==0.25.0")
            return None
            
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("Missing dependency: 'openai' package is not installed.")
            logger.error("Please install it with: pip install openai")
            return None
        
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

def _make_api_call(api_params, model):
    """
    Make an API call with rate limiting
    
    Args:
        api_params: The parameters for the API call
        model: The model name for rate limiting tracking
        
    Returns:
        The API response or a default response on error
    """
    client = get_openai_client()
    if not client:
        raise Exception("Failed to initialize OpenAI client")
    
    try:
        # Make the API call
        logger.info(f"Making API call to model: {model}")
        response = client.chat.completions.create(**api_params)
        return response
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise

def generate(session, input_data):
    """
    Generate a response using OpenAI API with rate limiting
    
    Args:
        session: The current session object to store results
        input_data: Dict containing:
            - type: Generation type ('answer', 'followup', or 'structured')
            - system: System prompt
            - user: User message to respond to
            - temperature: Optional temperature setting (default 0.7)
            - model: Optional model name (default gpt-4)
            - include_history: Optional flag to include chat history (default True)
            - response_format: Required for 'structured' type - contains JSON schema definition
    
    Returns:
        The generated text or JSON object for structured types
    """
    logger.info(f"Generate function received input_data: {input_data}")
    
    # Determine generation type (answer, followup, or structured)
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
    
    # Prepare API parameters
    api_params = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    # For structured output, add response_format parameter
    if generation_type == 'structured':
        if 'response_format' not in input_data:
            error_message = "response_format is required for structured generation type"
            logger.error(error_message)
            session['error'] = error_message
            session['generation'] = "I couldn't generate a structured response because the schema is missing."
            return session['generation']
        
        # Get the JSON schema from input_data
        json_schema = input_data.get('response_format')
        
        # Use function calling instead of response_format
        function_name = input_data.get('function_name', 'get_structured_data')
        function_description = input_data.get('function_description', 'Generate structured data based on the provided schema')
        
        # Create the function definition
        function_def = {
            "name": function_name,
            "description": function_description,
            "parameters": json_schema
        }
        
        # Add function calling parameters to API params
        api_params["tools"] = [{"type": "function", "function": function_def}]
        api_params["tool_choice"] = {"type": "function", "function": {"name": function_name}}
        
        logger.info(f"Using function calling with schema: {json_schema}")
        
        # We need to remove response_format if it was added
        if "response_format" in api_params:
            del api_params["response_format"]
    
    # Use the rate limiter to make the API call
    limiter = get_openai_limiter()
    
    # Create a function to execute the API call
    def execute_api_call():
        try:
            # Make the API call using our helper function
            response = _make_api_call(api_params, model)
            
            # Extract the generated text
            generated_text = response.choices[0].message.content
            
            # For structured output, parse the JSON
            if generation_type == 'structured':
                try:
                    # For function calling, we need to get the arguments from the tool calls
                    if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                        # Get the function arguments (which is a JSON string)
                        generated_text = response.choices[0].message.tool_calls[0].function.arguments
                    
                    # Parse the JSON response
                    generated_json = json.loads(generated_text)
                    logger.info(f"Successfully parsed structured JSON response")
                    
                    # Store both the raw text and parsed JSON in the session
                    session['generation_raw'] = generated_text
                    session['generation'] = generated_json
                    
                    return generated_json
                except json.JSONDecodeError as e:
                    error_message = f"Failed to parse structured JSON response: {str(e)}"
                    logger.error(error_message)
                    session['error'] = error_message
                    session['generation_raw'] = generated_text
                    session['generation'] = {}
                    return {}
            
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
            elif generation_type == 'structured':
                session['generation'] = {}
                return {}
            else:
                session['generation'] = "I'm sorry, I encountered an error while generating a response. Please check the API key or try again."
                return session['generation']
    
    # Queue the API request with the rate limiter
    # This is a blocking call that will execute when a token is available
    limiter.queue_request(execute_api_call, model)
    
    # Return the result from the session
    return session.get('generation', "I'm processing your request...")

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

"""
Example usage for the structured generation type:

```python
# Session object to store results
session = {}

# Example JSON schema for a product recommendation
product_schema = {
    "type": "object",
    "properties": {
        "product_name": {
            "type": "string",
            "description": "The name of the recommended product"
        },
        "price_range": {
            "type": "object",
            "properties": {
                "min": {
                    "type": "number",
                    "description": "Minimum price in USD"
                },
                "max": {
                    "type": "number",
                    "description": "Maximum price in USD"
                }
            },
            "required": ["min", "max"]
        },
        "features": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of key product features"
        },
        "rating": {
            "type": "number",
            "description": "Estimated product rating on a scale of 1-5"
        },
        "explanation": {
            "type": "string",
            "description": "Explanation of why this product is recommended"
        }
    },
    "required": ["product_name", "price_range", "features", "rating", "explanation"]
}

# Input data for structured generation
input_data = {
    "type": "structured",
    "system": "You are a product recommendation assistant that helps users find the best products based on their needs.",
    "user": "I need a laptop for video editing, budget around $2000",
    "temperature": 0.7,
    "model": "gpt-4-turbo",
    "function_name": "recommend_product",
    "function_description": "Generate a product recommendation based on user requirements",
    "response_format": product_schema
}

# Generate structured response
result = generate(session, input_data)

# Access the structured data
print(f"Recommended product: {result['product_name']}")
print(f"Price range: ${result['price_range']['min']} - ${result['price_range']['max']}")
print(f"Features: {', '.join(result['features'])}")
print(f"Rating: {result['rating']}/5")
print(f"Explanation: {result['explanation']}")
```

The result will be a JSON object that can be accessed like a dictionary:

```json
{
  "product_name": "MacBook Pro 16-inch",
  "price_range": {
    "min": 1999.0,
    "max": 2499.0
  },
  "features": [
    "M3 Pro or M3 Max chip",
    "16GB to 32GB unified memory",
    "1TB SSD storage",
    "16-inch Liquid Retina XDR display",
    "Dedicated GPU cores for video rendering"
  ],
  "rating": 4.8,
  "explanation": "The MacBook Pro 16-inch is ideal for video editing due to its powerful M3 chip, which excels at video rendering tasks. The large high-resolution display provides accurate color representation, and the unified memory architecture allows for faster video processing. It fits within your $2000 budget for the base model, though you may want to consider upgrading memory if your video projects are complex."
}
```

In a Neo4j workflow context, this would allow accessing structured fields in subsequent steps:

```cypher
CREATE (n:STEP {
  id: 'product-recommendation',
  function: 'generate.generate',
  input: '{
    "type": "structured", 
    "system": "You are a product recommendation assistant...", 
    "user": "@{get-requirements}.response", 
    "function_name": "recommend_product",
    "function_description": "Generate a product recommendation based on user requirements",
    "response_format": {...schema object...}
  }'
})

// Then in a next step, access specific fields from the result
CREATE (m:STEP {
  id: 'display-price',
  function: 'some.function',
  input: '{"min_price": "@{product-recommendation}.price_range.min", "max_price": "@{product-recommendation}.price_range.max"}'
})
```
"""
