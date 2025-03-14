import os
import logging
import requests
import json
import time
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

def setup():
    """Run the setup script to ensure workflow is correct"""
    # Check if the app is already running
    try:
        response = requests.get("http://localhost:5001/")
        logger.info("App is already running on port 5001")
    except:
        logger.info("Starting app in background")
        # Import os here to avoid issues with Flask context
        import subprocess
        subprocess.Popen(["python", "app_fixed.py"])
        # Wait for app to start
        for i in range(10):
            try:
                response = requests.get("http://localhost:5001/")
                logger.info("App started successfully")
                break
            except:
                logger.info(f"Waiting for app to start (attempt {i+1}/10)")
                time.sleep(1)
        else:
            logger.error("Failed to start app")
            return False
    
    return True

def check_variable_resolution():
    """Test variable resolution in the workflow"""
    logger.info("Starting test of variable resolution")
    
    # Step 1: Start a chat session
    response = requests.post("http://localhost:5001/start_chat")
    if response.status_code != 200:
        logger.error(f"Failed to start chat: {response.status_code} {response.text}")
        return False
    
    logger.info("Chat started successfully")
    
    # The first response will be awaiting input with the statement
    data = response.json()
    if not data.get('awaiting_input', False):
        logger.error("Expected to be awaiting input after starting chat")
        return False
    
    logger.info(f"Initial prompt: {data.get('statement', 'No statement found')}")
    
    # Step 2: Send a test message with both sentiment and animal
    test_message = "I love goats and they are wonderful animals"
    
    response = requests.post(
        "http://localhost:5001/send_message", 
        json={"message": test_message}
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to send message: {response.status_code} {response.text}")
        return False
    
    # After sending the message, the workflow processes it
    # We need to continue processing until we get a non-input response
    max_attempts = 5
    attempts = 0
    reply_with_variables = False
    
    while attempts < max_attempts:
        attempts += 1
        data = response.json()
        logger.info(f"Response attempt {attempts}: {data}")
        
        # If we're not awaiting input anymore, check the reply
        if not data.get('awaiting_input', False) and 'reply' in data:
            logger.info(f"Found reply in response: {data['reply']}")
            
            # Check if this reply contains the resolved variables
            if 'goat' in data['reply'] and ('positive' in data['reply'].lower() or 'love' in data['reply'].lower()):
                reply_with_variables = True
                break
        
        # If still awaiting input or processing, continue
        logger.info("Continuing workflow processing...")
        response = requests.post(
            "http://localhost:5001/continue_processing",
            json={}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to continue processing: {response.status_code} {response.text}")
            return False
    
    # Check if we found a reply with resolved variables
    if not reply_with_variables:
        logger.error("Did not find a reply with resolved variables after multiple attempts")
        
        # One last check of variables in the final data
        data = response.json()
        logger.info(f"Final response data: {data}")
        
        # The variable @{analyze-input}.is_positive should not appear in the response
        if '@{analyze-input}.is_positive' in data.get('reply', ''):
            logger.error("Found unresolved variable @{analyze-input}.is_positive in response")
        
        # The variable @{analyze-input}.feedback should not appear in the response
        if '@{analyze-input}.feedback' in data.get('reply', ''):
            logger.error("Found unresolved variable @{analyze-input}.feedback in response")
        
        return False
    
    logger.info("Variable resolution test passed!")
    return True

def main():
    """Run tests to verify variable handling in the workflow"""
    logger.info("Starting variable handling tests")
    
    if not setup():
        logger.error("Setup failed")
        return
    
    success = check_variable_resolution()
    
    if success:
        logger.info("All tests passed!")
    else:
        logger.error("Tests failed!")

if __name__ == "__main__":
    main() 