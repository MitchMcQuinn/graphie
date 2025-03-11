#!/usr/bin/env python
import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Load environment variables from .env.local
env_path = project_root / '.env.local'
load_result = load_dotenv(dotenv_path=env_path)
logger.info(f"Loading .env.local: {'Success' if load_result else 'Failed'}")

# Get the OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    # Show a masked version of the key for security
    masked_key = api_key[:4] + '****' + api_key[-4:] if len(api_key) > 8 else '********'
    logger.info(f"Found API key: {masked_key}")
else:
    logger.error("API key not found in .env.local")
    sys.exit(1)

# Import openai after setting the API key
try:
    import openai
    from openai import OpenAI
    logger.info(f"OpenAI package version: {openai.__version__}")
    
    # Set the API key
    openai.api_key = api_key
    logger.info("Set API key for OpenAI package")
    
    # Create a client
    client = OpenAI(api_key=api_key)
    logger.info("Created OpenAI client")
    
    # Make a test API call
    logger.info("Making test API call...")
    response = client.chat.completions.create(
        model="gpt-4-turbo",  # Using a less expensive model for testing
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, this is a test message from Graphie. Please respond with 'OpenAI integration is working!' if you receive this."}
        ],
        max_tokens=50
    )
    
    # Extract and log the response
    response_text = response.choices[0].message.content
    logger.info(f"Response from OpenAI: {response_text}")
    logger.info("✅ Test successful! OpenAI integration is working.")
    
except ImportError as e:
    logger.error(f"Error importing OpenAI: {e}")
    logger.error("Please install the OpenAI package with: pip install openai")
    sys.exit(1)
    
except Exception as e:
    logger.error(f"Error calling OpenAI API: {e}")
    logger.error("Test failed. OpenAI integration is not working.")
    sys.exit(1)

# Print information about the current environment
logger.info("\nEnvironment Information:")
logger.info(f"Python version: {sys.version}")
logger.info(f"OpenAI package version: {openai.__version__}")
logger.info(f".env.local path: {env_path}")
logger.info(f"Current working directory: {os.getcwd()}")

# Compare the openai import in utils/generate.py
generate_py_path = project_root / 'utils' / 'generate.py'
if generate_py_path.exists():
    with open(generate_py_path, 'r') as f:
        generate_py = f.read()
        
    logger.info("\nAnalyzing utils/generate.py:")
    if "from openai import OpenAI" in generate_py:
        logger.info("✅ utils/generate.py imports OpenAI client correctly")
    else:
        logger.info("❌ utils/generate.py may be using an outdated import method")
        logger.info("Recommendation: Update utils/generate.py to use 'from openai import OpenAI'")

    if "OpenAI(" in generate_py:
        logger.info("✅ utils/generate.py instantiates an OpenAI client")
    else:
        logger.info("❌ utils/generate.py may be using the deprecated global client")
        logger.info("Recommendation: Update to use client = OpenAI(api_key=openai.api_key)")

if __name__ == "__main__":
    # Script was run directly
    logger.info("Script completed successfully") 