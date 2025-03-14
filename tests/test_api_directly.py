import requests
import logging
import json
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api():
    """Test the API directly, bypassing the need for workflow steps"""
    # 1. Start a session
    logger.info("Starting a new chat session")
    response = requests.post("http://localhost:5001/start_chat")
    
    if response.status_code != 200:
        logger.error(f"Failed to start chat: {response.status_code}")
        return
    
    # 2. Get the initial session data
    initial_data = response.json()
    logger.info(f"Initial data: {initial_data}")
    
    # 3. Send a test message with animal and sentiment
    logger.info("Sending test message")
    test_message = "I love goats and they are wonderful animals"
    
    response = requests.post(
        "http://localhost:5001/send_message",
        json={"message": test_message}
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to send message: {response.status_code}")
        return
    
    # 4. Process the response
    data = response.json()
    logger.info(f"Response to message: {data}")
    
    # 5. Continue processing until we get a meaningful response 
    # or reach a maximum number of attempts
    max_attempts = 5
    for i in range(max_attempts):
        logger.info(f"Continue processing attempt {i+1}/{max_attempts}")
        
        response = requests.post(
            "http://localhost:5001/continue_processing",
            json={}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to continue processing: {response.status_code}")
            break
        
        data = response.json()
        logger.info(f"Continue processing response: {data}")
        
        # Check if we have a meaningful reply
        if not data.get('awaiting_input', False) and 'reply' in data:
            if '@{' not in data['reply']:
                logger.info(f"Found properly resolved reply: {data['reply']}")
                
                # Check for specific content
                if 'goat' in data['reply']:
                    logger.info("Success: Found 'goat' in the reply")
                else:
                    logger.warning("Did not find 'goat' in the reply")
                
                if 'positive' in data['reply'].lower():
                    logger.info("Success: Found 'positive' sentiment in the reply")
                else:
                    logger.warning("Did not find 'positive' sentiment in the reply")
                
                break
            else:
                logger.warning(f"Found unresolved variables in reply: {data['reply']}")
        
        # If we're still awaiting input, we'll need to continue in the next iteration
        if data.get('awaiting_input', False):
            logger.info("Still awaiting input, continuing...")
        else:
            logger.info("Not awaiting input but didn't find a reply yet")
    
    logger.info("Test completed")

if __name__ == "__main__":
    logger.info("Starting API direct test")
    test_api()
    logger.info("API test completed") 