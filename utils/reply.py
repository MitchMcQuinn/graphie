import logging
import json
from utils.session_manager import get_session_manager
from utils.resolve_variable import process_variables, resolve_variable
from utils.database import get_neo4j_driver

logger = logging.getLogger(__name__)

def reply(session, input_data):
    """
    Simply forwards a response to the user in the chat window
    
    Args:
        session: The current session object containing session_id
        input_data: Dict containing:
            - response: The text to display to the user
            - or:
            - reply: The text to display to the user
    
    Returns:
        The reply that was sent
    """
    logger.info(f"Reply function received input_data: {input_data}")
    
    # Get the Neo4j driver
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Neo4j driver not available")
        return {"error": "Neo4j connection unavailable"}
    
    # Get the session manager
    session_manager = get_session_manager(driver)
    if not session_manager:
        logger.error("Session manager not available")
        return {"error": "Session manager unavailable"}
    
    # Get the session_id
    session_id = session['id']
    
    # First process the entire input data for any variable references
    input_data = process_variables(driver, session_id, input_data)
    
    # Handle either 'response' or 'reply' field
    if 'response' in input_data:
        reply_text = input_data['response']
    else:
        reply_text = input_data.get('reply', '')
    
    # Process any variable references in the reply text
    # This is a second check to make sure any nested variables are resolved
    if isinstance(reply_text, str) and '@{' in reply_text:
        # Handle SESSION_ID special case first
        if 'SESSION_ID' in reply_text:
            reply_text = reply_text.replace('SESSION_ID', session_id)
            logger.info(f"Replaced SESSION_ID in reply_text: {reply_text}")
        
        # Process variable references
        resolved_text = process_variables(driver, session_id, reply_text)
        
        # Check if resolution was successful
        if resolved_text != reply_text:
            logger.info(f"Successfully resolved variables: {reply_text} -> {resolved_text}")
            reply_text = resolved_text
        else:
            logger.warning(f"Failed to resolve variables in: {reply_text}")
            
            # Try direct resolution as a fallback
            # This is helpful for cases like @{SESSION_ID}.step_id.key
            if reply_text.startswith('@{') and reply_text.endswith('}'):
                # Try direct resolution since it's a complete variable reference
                direct_result = resolve_variable(driver, session_id, reply_text)
                if direct_result != reply_text:
                    logger.info(f"Direct resolution successful: {reply_text} -> {direct_result}")
                    reply_text = direct_result
    
    # If the reply is empty, provide a fallback
    if not reply_text or reply_text.startswith('.'):
        reply_text = "I'm sorry, I wasn't able to generate a proper response. Could you please try again?"
        logger.warning("Empty or invalid reply text, using fallback message")
    
    # Final check for unresolved variables, just in case
    if isinstance(reply_text, str) and '@{' in reply_text:
        logger.warning(f"Still have unresolved variables in: {reply_text}")
        
        # Try manual extraction and resolution as a last resort
        if reply_text.startswith('@{') and '}' in reply_text:
            # Extract the variable parts manually
            var_content = reply_text.split('@{')[1].split('}')[0]
            logger.info(f"Extracted variable content: {var_content}")
            
            parts = var_content.split('.')
            if len(parts) >= 3:
                # Format: session_id.step_id.key
                target_session_id = parts[0]
                step_id = parts[1]
                key = parts[2]
                
                # Access memory directly
                try:
                    memory = session_manager.get_memory(target_session_id)
                    if step_id in memory and memory[step_id] and len(memory[step_id]) > 0:
                        latest_output = memory[step_id][-1]
                        if key in latest_output:
                            value = latest_output[key]
                            logger.info(f"Manual resolution successful: {reply_text} -> {value}")
                            reply_text = value
                except Exception as e:
                    logger.error(f"Manual resolution failed: {str(e)}")
    
    logger.info(f"Final reply text: {reply_text}")
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    try:
        status = session_manager.get_session_status(session_id)
        if 'next_steps' in status and status['next_steps'] and len(status['next_steps']) > 0:
            current_step_id = status['next_steps'][0]
    except Exception as e:
        logger.warning(f"Failed to get current step ID: {str(e)}")
    
    # Store this reply in the session memory
    step_id = f"reply-{current_step_id}"
    session_manager.store_memory(session_id, step_id, {'reply': reply_text})
    
    # Add the reply to chat history
    session_manager.add_assistant_message(session_id, reply_text)
    
    # Make sure we're not waiting for input from the user
    session_manager.set_session_status(session_id, 'active')
    
    return {
        'reply': reply_text
    }

# Alias for the reply function to match the Neo4j workflow
def respond(session, input_data):
    """
    Alias for the reply function to match the Neo4j workflow
    
    Args:
        session: The current session object
        input_data: The input data to process
        
    Returns:
        The reply that was sent
    """
    return reply(session, input_data)
