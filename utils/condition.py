"""
utils/condition.py
----------------
This module provides condition functions for workflow branching.

These functions evaluate various conditions on session data
to determine which workflow paths should be followed.
"""

import logging

# Set up logging
logger = logging.getLogger(__name__)

def equals(session, input_data):
    """
    Check if a value equals a specified value
    
    Args:
        session: The current session object
        input_data: Dict containing:
            - value: The value to check
            - equals: The value to compare against
            
    Returns:
        True if the values are equal, False otherwise
    """
    value = input_data.get('value')
    equals_value = input_data.get('equals')
    
    # Convert string representations of booleans
    if isinstance(value, str) and value.lower() in ['true', 'false']:
        if value.lower() == 'true':
            value = True
        else:
            value = False
            
    if isinstance(equals_value, str) and equals_value.lower() in ['true', 'false']:
        if equals_value.lower() == 'true':
            equals_value = True
        else:
            equals_value = False
    
    # Log the comparison
    logger.info(f"Checking if {value} equals {equals_value}")
    
    # Compare the values
    result = value == equals_value
    logger.info(f"Equals condition result: {result}")
    
    return result

def not_equals(session, input_data):
    """
    Check if a value does not equal a specified value
    
    Args:
        session: The current session object
        input_data: Dict containing:
            - value: The value to check
            - equals: The value to compare against
            
    Returns:
        True if the values are not equal, False otherwise
    """
    # Use the equals function and negate the result
    return not equals(session, input_data)

def contains(session, input_data):
    """
    Check if a string contains a specified substring
    
    Args:
        session: The current session object
        input_data: Dict containing:
            - value: The string to check
            - contains: The substring to look for
            
    Returns:
        True if the string contains the substring, False otherwise
    """
    value = str(input_data.get('value', ''))
    contains_value = str(input_data.get('contains', ''))
    
    # Log the comparison
    logger.info(f"Checking if '{value}' contains '{contains_value}'")
    
    # Check for substring
    result = contains_value in value
    logger.info(f"Contains condition result: {result}")
    
    return result

def greater_than(session, input_data):
    """
    Check if a numeric value is greater than a specified value
    
    Args:
        session: The current session object
        input_data: Dict containing:
            - value: The value to check
            - greater_than: The value to compare against
            
    Returns:
        True if the value is greater than the specified value, False otherwise
    """
    try:
        value = float(input_data.get('value', 0))
        greater_than_value = float(input_data.get('greater_than', 0))
        
        # Log the comparison
        logger.info(f"Checking if {value} > {greater_than_value}")
        
        # Compare the values
        result = value > greater_than_value
        logger.info(f"Greater than condition result: {result}")
        
        return result
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting values to float: {str(e)}")
        return False

def less_than(session, input_data):
    """
    Check if a numeric value is less than a specified value
    
    Args:
        session: The current session object
        input_data: Dict containing:
            - value: The value to check
            - less_than: The value to compare against
            
    Returns:
        True if the value is less than the specified value, False otherwise
    """
    try:
        value = float(input_data.get('value', 0))
        less_than_value = float(input_data.get('less_than', 0))
        
        # Log the comparison
        logger.info(f"Checking if {value} < {less_than_value}")
        
        # Compare the values
        result = value < less_than_value
        logger.info(f"Less than condition result: {result}")
        
        return result
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting values to float: {str(e)}")
        return False

def true(session, input_data):
    """
    Always returns True
    
    This function is useful for creating unconditional paths
    that should always be followed in parallel.
    
    Args:
        session: The current session object
        input_data: Not used
            
    Returns:
        Always True
    """
    logger.info("True condition - always returns True")
    return True 