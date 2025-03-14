import os
import logging
import json
from dotenv import load_dotenv
from utils.analyze import analyze_input
from utils.structured_generation import format_analysis
from utils.fixed_reply import fixed_reply

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_session_variables():
    """
    Test session variable handling by simulating workflow steps
    with predefined inputs and examining the session contents
    """
    # Create a mock session dictionary to track state
    session = {}
    
    # Step 1: Simulate user input
    user_input = "I love goats"
    session['user_input'] = user_input
    logger.info(f"Starting test with user input: {user_input}")
    
    # Step 2: Test animal extraction
    extract_animal_input = {
        "function": "extract_animal_names",
        "input": user_input
    }
    
    logger.info(f"Testing animal extraction with input: {extract_animal_input}")
    result = analyze_input(session, extract_animal_input)
    logger.info(f"Animal extraction result: {result}")
    logger.info(f"Session after animal extraction: {session}")
    
    # Step 3: Test sentiment analysis
    sentiment_input = {
        "function": "sentiment_analysis",
        "input": user_input
    }
    
    logger.info(f"Testing sentiment analysis with input: {sentiment_input}")
    result = analyze_input(session, sentiment_input)
    logger.info(f"Sentiment analysis result: {result}")
    logger.info(f"Session after sentiment analysis: {session}")
    
    # Step 4: Test problematic provide-analysis step
    provide_analysis_input = {
        "is_positive": session.get('is_positive', 'MISSING'),
        "feedback": session.get('feedback', 'MISSING')
    }
    
    logger.info(f"Testing provide-analysis with input: {provide_analysis_input}")
    try:
        result = format_analysis(session, provide_analysis_input)
        logger.info(f"Format analysis result: {result}")
    except Exception as e:
        logger.error(f"Error in format_analysis: {str(e)}")
    logger.info(f"Session after format analysis: {session}")
    
    # Step 5: Test return-animal variable substitution
    return_animal_input = {
        "reply": f"I notice you mentioned @{{extract-animal}}.animals. @{{analyze-input}}.sentiment Would you like to know more about this animal?"
    }
    
    # Manually replace variables for testing
    if 'animals' in session:
        return_animal_input['reply'] = return_animal_input['reply'].replace('@{extract-animal}.animals', session['animals'])
    if 'sentiment' in session:
        return_animal_input['reply'] = return_animal_input['reply'].replace('@{analyze-input}.sentiment', session['sentiment'])
    
    logger.info(f"Testing return-animal with input: {return_animal_input}")
    result = fixed_reply(session, return_animal_input)
    logger.info(f"Fixed reply result: {result}")
    logger.info(f"Session after fixed reply: {session}")
    
    # Print final session state
    logger.info("==== FINAL SESSION STATE ====")
    for key, value in session.items():
        logger.info(f"{key}: {value}")
    
    # Analyze the output and suggest solutions
    logger.info("==== ANALYSIS OF ISSUES ====")
    if 'is_positive' not in session and 'feedback' not in session:
        logger.warning("The 'is_positive' and 'feedback' variables expected by provide-analysis are missing")
        logger.info("Solution: Update the analyze.py sentiment_analysis function to store these variables, or update the workflow to use the variables it does store ('sentiment')")
    
    if 'formatted_result' in session and '@{analyze-input}' in session['formatted_result']:
        logger.warning("The formatted_result contains unresolved variables")
        logger.info("Solution: Fix the variable resolution in the format_analysis function or replace it with a simpler implementation")

if __name__ == "__main__":
    logger.info("Starting session variable diagnostics")
    test_session_variables()
    logger.info("Diagnostics completed") 