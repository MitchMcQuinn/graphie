"""
utils/reply.py
----------------
This module provides a simple reply function that forwards responses to the user in the chat window.
"""

import logging
import json
from core.session_manager import get_session_manager
from core.resolve_variable import process_variables, resolve_variable
from core.database import get_neo4j_driver
import re

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
    logger.info(f"Processing reply for session: {session_id}")
    
    # Handle either 'response' or 'reply' field
    if 'response' in input_data:
        reply_text = input_data['response']
        logger.info(f"Using 'response' field: {reply_text}")
    else:
        reply_text = input_data.get('reply', '')
        logger.info(f"Using 'reply' field: {reply_text}")
    
    # Process any variable references in the reply text
    if isinstance(reply_text, str):
        try:
            logger.info(f"Processing variables in reply text: {reply_text}")
            
            # Find all variable references in the text
            pattern = r'@\{[^}]+\}(?:\.[^}\s]+\.[^}\s]+)?'
            matches = re.finditer(pattern, reply_text)
            
            # Process each match
            for match in matches:
                var_ref = match.group(0)
                logger.info(f"Found variable reference: {var_ref}")
                
                # Resolve the variable
                resolved = resolve_variable(driver, session_id, var_ref)
                logger.info(f"Resolved {var_ref} to: {resolved}")
                
                # Replace in the text
                if isinstance(resolved, (str, int, float, bool)):
                    reply_text = reply_text.replace(var_ref, str(resolved))
                else:
                    logger.warning(f"Can't embed complex object in string: {var_ref}")
            
            logger.info(f"Final reply text after variable resolution: {reply_text}")
            
        except Exception as e:
            logger.error(f"Failed to process variables: {str(e)}", exc_info=True)
    
    # If the reply is empty, provide a fallback
    if not reply_text or reply_text.startswith('.'):
        reply_text = "I'm sorry, I wasn't able to generate a proper response. Could you please try again?"
        logger.warning("Empty or invalid reply text, using fallback message")
    
    logger.info(f"Final reply text: {reply_text}")
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    try:
        status = session_manager.get_session_status(session_id)
        if 'next_steps' in status and status['next_steps'] and len(status['next_steps']) > 0:
            current_step_id = status['next_steps'][0]
            logger.info(f"Current step ID: {current_step_id}")
    except Exception as e:
        logger.error(f"Failed to get current step ID: {str(e)}", exc_info=True)
    
    # Store this reply in the session memory
    step_id = f"reply-{current_step_id}"
    try:
        session_manager.store_memory(session_id, step_id, {'reply': reply_text})
        logger.info(f"Stored reply in session memory for step: {step_id}")
    except Exception as e:
        logger.error(f"Failed to store reply in session memory: {str(e)}", exc_info=True)
    
    # Add the reply to chat history
    try:
        session_manager.add_assistant_message(session_id, reply_text)
        logger.info("Added reply to chat history")
    except Exception as e:
        logger.error(f"Failed to add reply to chat history: {str(e)}", exc_info=True)
    
    # Make sure we're not waiting for input from the user
    try:
        session_manager.set_session_status(session_id, 'active')
        logger.info("Set session status to active")
    except Exception as e:
        logger.error(f"Failed to set session status: {str(e)}", exc_info=True)
    
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
