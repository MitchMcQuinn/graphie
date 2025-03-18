"""
test_structured_output.py
-------------------------
Test script to demonstrate structured output generation with OpenAI.

This script shows how to use the updated generate.py to produce structured outputs
based on a provided JSON schema. It demonstrates:
1. Creating a schema
2. Passing it to the generate function 
3. Processing the structured result
"""

import os
import json
import logging
from flask import session as flask_session
from utils.generate import generate, get_openai_client

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_response():
    """Test generating a simple structured response with a default schema"""
    
    # Create a mock session for testing
    mock_session = {}
    
    # Basic input with no schema (will use default simple schema)
    input_data = {
        "system": "You are a helpful assistant providing clear, concise answers.",
        "user": "What are the three primary colors?",
        "temperature": 0.7
    }
    
    logger.info("Generating simple structured response...")
    result = generate(mock_session, input_data)
    
    logger.info(f"Result type: {type(result)}")
    logger.info(f"Generated structured output: {json.dumps(result, indent=2)}")
    logger.info(f"Session data after generation: {json.dumps(mock_session, indent=2)}")
    
    return result

def test_complex_response():
    """Test generating a complex structured response with a custom schema"""
    
    # Create a mock session for testing
    mock_session = {}
    
    # Define a more complex schema for a product recommendation
    schema = {
        "type": "object",
        "properties": {
            "recommendation": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the recommendation"
                    },
                    "summary": {
                        "type": "string",
                        "description": "A brief summary of the recommendation"
                    },
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Product name"
                                },
                                "price_range": {
                                    "type": "string",
                                    "description": "Approximate price range in USD"
                                },
                                "pros": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "Key advantages of this product"
                                },
                                "cons": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "Key disadvantages of this product"
                                },
                                "rating": {
                                    "type": "number",
                                    "minimum": 1,
                                    "maximum": 5,
                                    "description": "Rating from 1-5"
                                }
                            },
                            "required": ["name", "pros", "rating"]
                        }
                    },
                    "conclusion": {
                        "type": "string",
                        "description": "Final recommendation conclusion"
                    }
                },
                "required": ["title", "summary", "products", "conclusion"]
            },
            "response": {
                "type": "string", 
                "description": "A conversational response to the user's query"
            }
        },
        "required": ["recommendation", "response"]
    }
    
    # Input with the custom schema
    input_data = {
        "system": "You are a helpful product recommendation assistant with expertise in consumer electronics.",
        "user": "What are the best noise-cancelling headphones for travel?",
        "temperature": 0.7,
        "schema": schema,
        "schema_description": "Generate a structured product recommendation with detailed information for each product."
    }
    
    logger.info("Generating complex structured response...")
    result = generate(mock_session, input_data)
    
    logger.info(f"Result type: {type(result)}")
    logger.info(f"Generated structured output: {json.dumps(result, indent=2)}")
    logger.info(f"Session data after generation: {json.dumps(mock_session, indent=2)}")
    
    # Demonstrate how to access specific properties from the structured result
    if result and 'recommendation' in result:
        logger.info(f"\nRecommendation title: {result['recommendation']['title']}")
        logger.info(f"Number of products recommended: {len(result['recommendation']['products'])}")
        
        # Access the first product's details
        if result['recommendation']['products']:
            first_product = result['recommendation']['products'][0]
            logger.info(f"First product: {first_product['name']}")
            logger.info(f"Rating: {first_product['rating']}/5")
            logger.info(f"Pros: {', '.join(first_product['pros'])}")
    
    return result

def test_session_variable_access():
    """Test accessing structured output properties from session variables"""
    # Create a mock session for testing
    mock_session = {}
    
    # Define a schema for a factorial calculation
    schema = {
        "type": "object",
        "properties": {
            "calculation": {
                "type": "object",
                "properties": {
                    "number": {
                        "type": "integer",
                        "description": "The number to calculate factorial for"
                    },
                    "factorial": {
                        "type": "integer", 
                        "description": "The factorial result"
                    },
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Step-by-step calculation"
                    }
                },
                "required": ["number", "factorial", "steps"]
            },
            "response": {
                "type": "string",
                "description": "A conversational explanation of the factorial calculation"
            }
        },
        "required": ["calculation", "response"]
    }
    
    # Input with the factorial schema
    input_data = {
        "system": "You are a helpful math assistant that provides clear explanations.",
        "user": "Calculate the factorial of 5 and show your work.",
        "temperature": 0.0,  # Use 0 for deterministic results
        "schema": schema
    }
    
    logger.info("Generating factorial calculation...")
    result = generate(mock_session, input_data)
    
    # Demonstrate how to access the structured data from the session
    logger.info("\nAccessing structured data from session:")
    logger.info(f"Complete generation object: {mock_session.get('generation')}")
    logger.info(f"Response text: {mock_session.get('generation_response')}")
    logger.info(f"Factorial result: {mock_session.get('generation_calculation', {}).get('factorial')}")
    
    # Accessing nested properties through flattened session keys
    logger.info("\nAccessing flattened properties:")
    for key in mock_session:
        if key.startswith('generation_'):
            logger.info(f"- {key}: {mock_session[key]}")
    
    return result

def run_tests():
    """Run all the structured output tests"""
    logger.info("==== Starting Structured Output Tests ====")
    
    # Test 1: Simple schema
    logger.info("\n\n==== Test 1: Simple Schema Response ====")
    simple_result = test_simple_response()
    
    # Test 2: Complex schema
    logger.info("\n\n==== Test 2: Complex Schema Response ====")
    complex_result = test_complex_response()
    
    # Test 3: Session variable access
    logger.info("\n\n==== Test 3: Session Variable Access ====")
    session_result = test_session_variable_access()
    
    logger.info("\n\n==== All Tests Completed ====")

if __name__ == "__main__":
    run_tests() 