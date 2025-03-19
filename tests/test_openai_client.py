import os
import pytest
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def test_openai_client_initialization():
    """Test that OpenAI client can be initialized correctly"""
    api_key = os.getenv('OPENAI_API_KEY')
    assert api_key is not None, "OPENAI_API_KEY not found in environment variables"
    
    # Test basic initialization with http_client
    http_client = httpx.Client(
        base_url="https://api.openai.com/v1",
        timeout=30.0
    )
    
    client = OpenAI(
        api_key=api_key,
        http_client=http_client
    )
    assert client is not None, "Failed to initialize OpenAI client"
    
    # Test that client can make a simple API call
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7
        )
        assert response is not None, "Failed to get response from OpenAI API"
        assert response.choices is not None, "Response choices is None"
        assert len(response.choices) > 0, "No choices in response"
    except Exception as e:
        pytest.fail(f"Failed to make API call: {str(e)}")
    finally:
        http_client.close()

def test_openai_client_with_proxies():
    """Test that OpenAI client initialization fails with proxies parameter"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    # This should raise an error as proxies is not a valid parameter
    with pytest.raises(TypeError) as exc_info:
        client = OpenAI(
            api_key=api_key,
            proxies={"http": "http://proxy.example.com:8080"}
        )
    
    assert "unexpected keyword argument 'proxies'" in str(exc_info.value), \
        "Expected error about unexpected 'proxies' argument"

def test_openai_client_with_custom_config():
    """Test OpenAI client with custom configuration"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Test with custom http_client configuration
    http_client = httpx.Client(
        base_url="https://api.openai.com/v1",
        timeout=30.0
    )
    
    client = OpenAI(
        api_key=api_key,
        http_client=http_client
    )
    assert client is not None, "Failed to initialize OpenAI client with custom config"
    http_client.close() 