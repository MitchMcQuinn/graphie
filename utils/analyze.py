"""
utils/analyze.py
----------------
This module provides analysis functions for user input,
including animal name extraction and sentiment analysis.
"""

import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

def analyze_input(session, input_data):
    """
    Generic analyzer that dispatches to specific analysis functions
    
    Args:
        session: The current session object
        input_data: Dict containing:
            - function: The specific analysis function to run
            - input: The text to analyze
            
    Returns:
        The result of the analysis
    """
    function_name = input_data.get('function')
    input_text = input_data.get('input', '')
    
    logger.info(f"Analyzing input with function '{function_name}': {input_text[:50]}...")
    
    # Call the appropriate function based on the function_name
    if function_name == 'extract_animal_names':
        return extract_animal_names(session, input_text)
    elif function_name == 'sentiment_analysis':
        return sentiment_analysis(session, input_text)
    else:
        logger.warning(f"Unknown analysis function: {function_name}")
        return {"error": f"Unknown analysis function: {function_name}"}

def extract_animal_names(session, input_text):
    """
    Extract animal names from the input text
    
    Args:
        session: The current session object
        input_text: The text to analyze
        
    Returns:
        Dict with extracted animal names
    """
    logger.info(f"Extracting animal names from: {input_text}")
    
    # Common animals to look for - could be expanded
    animal_list = [
        'goat', 'goats', 
        'sheep', 
        'pig', 'pigs',
        'cow', 'cows',
        'chicken', 'chickens',
        'duck', 'ducks',
        'horse', 'horses',
        'dog', 'dogs',
        'cat', 'cats'
    ]
    
    found_animals = []
    
    # Convert to lowercase for case-insensitive matching
    text_lower = input_text.lower()
    
    # Check for each animal in the text
    for animal in animal_list:
        if animal in text_lower:
            # Add the base form (singular) of the animal
            base_animal = animal
            if animal.endswith('s') and animal != 'sheep':  # sheep is both singular and plural
                base_animal = animal[:-1]
            
            if base_animal not in found_animals:
                found_animals.append(base_animal)
    
    # Store in session and return result
    if found_animals:
        result = ', '.join(found_animals)
        logger.info(f"Found animals: {result}")
        session['animals'] = result
        return {"animals": result}
    else:
        logger.info("No animals found in the text")
        session['animals'] = "no animals"
        return {"animals": "no animals"}

def sentiment_analysis(session, input_text):
    """
    Simple sentiment analysis on the input text
    
    Args:
        session: The current session object
        input_text: The text to analyze
        
    Returns:
        Dict with sentiment analysis result
    """
    logger.info(f"Analyzing sentiment of: {input_text}")
    
    # Very simple sentiment analysis with keyword matching
    # In a real system, you'd use a more sophisticated approach
    
    positive_words = ['love', 'like', 'enjoy', 'happy', 'good', 'great', 'excellent', 'wonderful', 'amazing']
    negative_words = ['hate', 'dislike', 'terrible', 'awful', 'bad', 'worst', 'horrible', 'disgusting']
    
    # Convert to lowercase for case-insensitive matching
    text_lower = input_text.lower()
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    # Determine sentiment based on counts
    if positive_count > negative_count:
        sentiment = "positive"
        sentiment_msg = "You seem to have positive feelings about this."
        is_positive = True
        feedback = "Your message contains positive sentiment."
    elif negative_count > positive_count:
        sentiment = "negative"
        sentiment_msg = "You seem to have negative feelings about this."
        is_positive = False
        feedback = "Your message contains negative sentiment."
    else:
        sentiment = "neutral"
        sentiment_msg = "You seem to have neutral feelings about this."
        is_positive = None
        feedback = "Your message appears to be neutral."
    
    # Store in session and return result
    session['sentiment'] = sentiment_msg
    session['is_positive'] = is_positive  # Add this for compatibility with show-analysis
    session['feedback'] = feedback  # Add this for compatibility with show-analysis
    logger.info(f"Sentiment analysis result: {sentiment}")
    logger.info(f"Added compatibility variables: is_positive={is_positive}, feedback={feedback}")
    
    return {"sentiment": sentiment_msg, "is_positive": is_positive, "feedback": feedback} 