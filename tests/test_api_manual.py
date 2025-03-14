import requests
import json
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app endpoints
BASE_URL = "http://localhost:5001"
START_CHAT_URL = f"{BASE_URL}/start_chat"
SEND_MESSAGE_URL = f"{BASE_URL}/send_message"
CONTINUE_PROCESSING_URL = f"{BASE_URL}/continue_processing"
DEBUG_URL = f"{BASE_URL}/debug_workflow"

def test_manual_api():
    """Test the API manually with step by step control"""
    # 1. Start a chat session
    logger.info("==== STARTING CHAT SESSION ====")
    response = requests.post(START_CHAT_URL)
    
    if response.status_code != 200:
        logger.error(f"Failed to start chat: {response.status_code}")
        return
    
    logger.info(f"Start chat response: {response.json()}")
    
    # 2. Check debug info
    logger.info("==== CHECKING DEBUG INFO ====")
    response = requests.get(DEBUG_URL)
    if response.status_code == 200:
        logger.info(f"Debug info: {json.dumps(response.json(), indent=2)}")
    
    # 3. Send a message with animal and sentiment
    logger.info("==== SENDING USER MESSAGE ====")
    message = "I love goats and they are wonderful animals"
    
    response = requests.post(
        SEND_MESSAGE_URL,
        json={"message": message}
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to send message: {response.status_code}")
        return
    
    logger.info(f"Send message response: {json.dumps(response.json(), indent=2)}")
    
    # 4. Check debug info again
    logger.info("==== CHECKING DEBUG INFO AFTER SENDING MESSAGE ====")
    response = requests.get(DEBUG_URL)
    if response.status_code == 200:
        logger.info(f"Debug info: {json.dumps(response.json(), indent=2)}")
    
    # 5. Continue processing several times
    for i in range(5):
        logger.info(f"==== CONTINUE PROCESSING #{i+1} ====")
        
        response = requests.post(CONTINUE_PROCESSING_URL)
        
        if response.status_code != 200:
            logger.error(f"Failed to continue processing: {response.status_code}")
            break
        
        result = response.json()
        logger.info(f"Continue processing response: {json.dumps(result, indent=2)}")
        
        # Check if we have a reply with resolved variables
        if not result.get('awaiting_input', False) and result.get('reply'):
            reply = result.get('reply', '')
            logger.info(f"Checking reply for resolved variables: {reply}")
            
            if '@{' in reply:
                logger.warning("Found unresolved variables in reply")
            else:
                logger.info("All variables properly resolved")
                
                # Check for specific content
                if 'goat' in reply:
                    logger.info("Success: Found 'goat' in the reply")
                else:
                    logger.warning("Did not find 'goat' in the reply")
                
                if 'positive' in reply.lower() or 'love' in reply.lower():
                    logger.info("Success: Found positive sentiment indication in the reply")
                else:
                    logger.warning("Did not find positive sentiment indication in the reply")
        
        # Check debug info
        logger.info(f"==== CHECKING DEBUG INFO AFTER CONTINUE #{i+1} ====")
        response = requests.get(DEBUG_URL)
        if response.status_code == 200:
            logger.info(f"Debug info: {json.dumps(response.json(), indent=2)}")
        
        # If no more pending steps, we're done
        if not result.get('has_pending_steps', False) and not result.get('awaiting_input', False):
            logger.info("No more pending steps, test complete")
            break
        
        # Short pause to make logs more readable
        time.sleep(0.5)

if __name__ == "__main__":
    logger.info("Starting manual API test")
    test_manual_api()
    logger.info("Manual API test completed") 