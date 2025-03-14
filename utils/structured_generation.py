import logging
import json
from utils.generate import generate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_input(session, input_data):
    """
    Custom wrapper for generate.generate that properly handles structured generation
    and stores the results in the session for easier access
    
    Args:
        session: The current session object
        input_data: Dict with parameters for generate.generate
    
    Returns:
        True to indicate success
    """
    logger.info(f"Analyze input function received input_data: {input_data}")
    
    # Call the standard generate function
    result = generate(session, input_data)
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
    logger.info("Final session data after analyze_input:")
    for key in session:
        if key in result_keys or key == 'structured_result':
            logger.info(f"  - {key}: {session[key]}")
    
    return result 

def format_analysis(session, input_data):
    """
    A simplified function to format any structured data from the session
    
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