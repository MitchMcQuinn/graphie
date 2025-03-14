#!/usr/bin/env python
import os
import sys
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Import the generate function
from utils.generate import generate

def test_structured_generation():
    """Test the structured generation functionality"""
    logger.info("Testing structured generation...")
    
    # Create a test session
    session = {}
    
    # Define a simple test schema
    test_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of a famous person"
            },
            "profession": {
                "type": "string",
                "description": "Their primary profession"
            },
            "birth_year": {
                "type": "number",
                "description": "Year they were born"
            },
            "famous_for": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "What they are famous for"
            }
        },
        "required": ["name", "profession", "birth_year", "famous_for"]
    }
    
    # Define input data
    input_data = {
        "type": "structured",
        "system": "You are a helpful assistant providing factual information.",
        "user": "Tell me about Albert Einstein",
        "temperature": 0.3,
        "model": "gpt-4-turbo",
        "function_name": "get_person_info",
        "function_description": "Get information about a famous person",
        "response_format": test_schema
    }
    
    try:
        # Generate the structured response
        result = generate(session, input_data)
        
        # Check if result is a dictionary
        if not isinstance(result, dict):
            logger.error(f"Expected result to be a dictionary, got {type(result)}")
            return False
            
        # Check if the required fields are present
        required_fields = ["name", "profession", "birth_year", "famous_for"]
        for field in required_fields:
            if field not in result:
                logger.error(f"Required field '{field}' missing from result")
                return False
                
        # Check if famous_for is a list
        if not isinstance(result["famous_for"], list):
            logger.error(f"Expected 'famous_for' to be a list, got {type(result['famous_for'])}")
            return False
                
        # Print the result in a pretty format
        logger.info("Structured generation successful!")
        logger.info(f"Name: {result['name']}")
        logger.info(f"Profession: {result['profession']}")
        logger.info(f"Birth Year: {result['birth_year']}")
        logger.info(f"Famous for:")
        for item in result["famous_for"]:
            logger.info(f"  - {item}")
            
        # Also print the raw result for reference
        logger.info("\nRaw result:")
        logger.info(json.dumps(result, indent=2))
        
        # Check if the original raw text is stored in the session
        if 'generation_raw' in session:
            logger.info("\nOriginal raw text from API:")
            logger.info(session['generation_raw'][:200] + "..." if len(session['generation_raw']) > 200 else session['generation_raw'])
            
        return True
        
    except Exception as e:
        logger.error(f"Error testing structured generation: {str(e)}")
        return False

def test_nested_structured_generation():
    """Test structured generation with nested schema"""
    logger.info("\nTesting nested structured generation...")
    
    # Create a test session
    session = {}
    
    # Define a more complex nested schema
    nested_schema = {
        "type": "object",
        "properties": {
            "movie": {
                "type": "string",
                "description": "Name of a popular movie"
            },
            "director": {
                "type": "string",
                "description": "Director of the movie"
            },
            "release_year": {
                "type": "number",
                "description": "Year the movie was released"
            },
            "ratings": {
                "type": "object",
                "properties": {
                    "imdb": {
                        "type": "number",
                        "description": "IMDb rating out of 10"
                    },
                    "rotten_tomatoes": {
                        "type": "number",
                        "description": "Rotten Tomatoes percentage"
                    }
                },
                "required": ["imdb", "rotten_tomatoes"]
            },
            "cast": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Actor name"
                        },
                        "character": {
                            "type": "string",
                            "description": "Character played"
                        }
                    },
                    "required": ["name", "character"]
                },
                "description": "Main cast of the movie"
            },
            "summary": {
                "type": "string",
                "description": "Brief plot summary"
            }
        },
        "required": ["movie", "director", "release_year", "ratings", "cast", "summary"]
    }
    
    # Define input data
    input_data = {
        "type": "structured",
        "system": "You are a movie information assistant.",
        "user": "Tell me about the movie The Matrix",
        "temperature": 0.3,
        "model": "gpt-4-turbo",
        "function_name": "get_movie_info",
        "function_description": "Get detailed information about a movie",
        "response_format": nested_schema
    }
    
    try:
        # Generate the structured response
        result = generate(session, input_data)
        
        # Check if result is a dictionary
        if not isinstance(result, dict):
            logger.error(f"Expected result to be a dictionary, got {type(result)}")
            return False
            
        # Check if nested objects are present and have correct structure
        if not isinstance(result.get("ratings"), dict):
            logger.error(f"Expected 'ratings' to be an object, got {type(result.get('ratings'))}")
            return False
            
        if not isinstance(result.get("cast"), list):
            logger.error(f"Expected 'cast' to be a list, got {type(result.get('cast'))}")
            return False
            
        # Print the result in a formatted way
        logger.info("Nested structured generation successful!")
        logger.info(f"Movie: {result['movie']} ({result['release_year']})")
        logger.info(f"Director: {result['director']}")
        logger.info(f"Ratings: IMDb {result['ratings']['imdb']}/10, Rotten Tomatoes {result['ratings']['rotten_tomatoes']}%")
        logger.info("Cast:")
        for actor in result["cast"]:
            logger.info(f"  - {actor['name']} as {actor['character']}")
        logger.info(f"Summary: {result['summary']}")
        
        # Print the raw nested result
        logger.info("\nRaw nested result:")
        logger.info(json.dumps(result, indent=2))
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing nested structured generation: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting structured generation tests...")
    
    # Run the simple test
    simple_result = test_structured_generation()
    
    # Run the nested test
    nested_result = test_nested_structured_generation()
    
    # Print overall results
    if simple_result and nested_result:
        logger.info("\n✅ All structured generation tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some structured generation tests failed!")
        sys.exit(1) 