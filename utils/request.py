"""
utils/request.py
----------------
This module provides a request function that pauses the workflow until a user response is received.
"""

import logging
import json
from core.session_manager import get_session_manager
from core.resolve_variable import resolve_variable
from core.database import get_neo4j_driver
import re

logger = logging.getLogger(__name__)

def _process_variables_with_fallback(driver, session_id, text):
    """
    Process variable references in a text string, using fallback values if variables can't be resolved.
    
    Args:
        driver: Neo4j driver instance
        session_id: Current session ID
        text: Text containing variable references and optional fallback values
        
    Returns:
        Tuple of (processed_text, needs_pending)
    """
    if not isinstance(text, str):
        return text, False
        
    try:
        logger.info(f"Processing variables in text: {text}")
        
        # Split on | to get the main text and fallback
        parts = text.split('|')
        main_text = parts[0].strip()
        fallback = parts[1].strip() if len(parts) > 1 else None
        
        # Find all variable references in the text
        pattern = r'@\{[^}]+\}(?:\.[^}\s]+\.[^}\s]+)?'
        matches = list(re.finditer(pattern, main_text))
        
        if not matches:
            return text, False
            
        # Process each match
        needs_pending = False
        processed_text = main_text
        
        for match in matches:
            var_ref = match.group(0)
            logger.info(f"Found variable reference: {var_ref}")
            
            # Resolve the variable
            resolved = resolve_variable(driver, session_id, var_ref)
            logger.info(f"Resolved {var_ref} to: {resolved}")
            
            # If resolution failed and we have a fallback, use it
            if resolved == var_ref:
                if fallback:
                    logger.info(f"Using fallback value: {fallback}")
                    processed_text = fallback
                    break
                else:
                    logger.info(f"No fallback value available for {var_ref}")
                    needs_pending = True
                    break
            
            # Replace in the text
            if isinstance(resolved, (str, int, float, bool)):
                processed_text = processed_text.replace(var_ref, str(resolved))
            else:
                logger.warning(f"Can't embed complex object in string: {var_ref}")
                needs_pending = True
                break
        
        logger.info(f"Final text after variable resolution: {processed_text}")
        return processed_text, needs_pending
        
    except Exception as e:
        logger.error(f"Failed to process variables: {str(e)}", exc_info=True)
        return text, True

def request(session, input_data):
    """
    Human-in-the-loop request function that pauses the workflow until a user response is received.
    This function sets up the session to await user input, storing the question or statement
    to be displayed to the user in the front-end.
    
    Since Flask handles requests synchronously, this function doesn't actually block execution.
    Instead, it marks the session as awaiting input, which is checked by the workflow engine
    and API endpoints to pause processing until user input is received.
    
    Args:
        session: The current session object containing session_id
        input_data: Dict containing:
            - statement: The question or statement to ask the user
            - query: Alternative name for statement
    
    Returns:
        A dict with status 'waiting_for_input' indicating a request has been initiated
    """
    logger.info(f"Request function received input_data: {input_data}")
    
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
    
    # Get the session ID
    session_id = session['id']
    logger.info(f"Processing request for session: {session_id}")
    
    # Extract the statement to show to the user
    # Support both 'statement' and 'query' parameter names
    statement = input_data.get('statement', input_data.get('query', 'What would you like to know?'))
    logger.info(f"Initial statement: {statement}")
    
    # Process variables with fallback handling
    processed_statement, needs_pending = _process_variables_with_fallback(driver, session_id, statement)
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    try:
        status = session_manager.get_session_status(session_id)
        if 'next_steps' in status and status['next_steps'] and len(status['next_steps']) > 0:
            current_step_id = status['next_steps'][0]
            logger.info(f"Current step ID: {current_step_id}")
    except Exception as e:
        logger.error(f"Failed to get current step ID: {str(e)}", exc_info=True)
    
    # Store the statement in session memory
    step_id_request = f"request-{current_step_id}"
    try:
        session_manager.store_memory(session_id, step_id_request, {'statement': processed_statement})
        logger.info(f"Stored request in session memory for step: {step_id_request}")
    except Exception as e:
        logger.error(f"Failed to store request in session memory: {str(e)}", exc_info=True)
    
    # Also store directly under the step ID for reference variable compatibility
    try:
        session_manager.store_memory(session_id, current_step_id, {'response': processed_statement})
        logger.info(f"Stored response in session memory for step: {current_step_id}")
    except Exception as e:
        logger.error(f"Failed to store response in session memory: {str(e)}", exc_info=True)
    
    # Set the session status based on variable resolution
    if needs_pending:
        try:
            session_manager.set_session_status(session_id, 'pending')
            logger.info("Set session status to pending due to unresolved variables")
        except Exception as e:
            logger.error(f"Failed to set session status: {str(e)}", exc_info=True)
    else:
        try:
            session_manager.set_session_status(session_id, 'awaiting_input')
            logger.info("Set session status to awaiting_input")
        except Exception as e:
            logger.error(f"Failed to set session status: {str(e)}", exc_info=True)
    
    # Add the statement to chat history
    try:
        session_manager.add_assistant_message(session_id, processed_statement)
        logger.info("Added statement to chat history")
    except Exception as e:
        logger.error(f"Failed to add statement to chat history: {str(e)}", exc_info=True)
    
    logger.info(f"Request function completed for session {session_id}, statement: {processed_statement}")
    
    # Return appropriate status based on variable resolution
    if needs_pending:
        return {
            'status': 'pending',
            'statement': processed_statement
        }
    else:
        return {
            'status': 'waiting_for_input',
            'statement': processed_statement
        }

def handle_user_response(session, user_response):
    """
    Handle the user's response to a request
    
    Args:
        session: The current session object containing session_id
        user_response: The user's response text
        
    Returns:
        Dict with status 'input_received'
    """
    logger.info(f"Handling user response: {user_response}")
    
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
    
    # Get the session ID
    session_id = session['id']
    logger.info(f"Processing user response for session: {session_id}")
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    try:
        status = session_manager.get_session_status(session_id)
        if 'next_steps' in status and status['next_steps'] and len(status['next_steps']) > 0:
            current_step_id = status['next_steps'][0]
            logger.info(f"Current step ID: {current_step_id}")
    except Exception as e:
        logger.error(f"Failed to get current step ID: {str(e)}", exc_info=True)
    
    # Store the user's response in session memory
    step_id_response = f"response-{current_step_id}"
    try:
        session_manager.store_memory(session_id, step_id_response, {'response': user_response})
        logger.info(f"Stored user response in session memory for step: {step_id_response}")
    except Exception as e:
        logger.error(f"Failed to store user response in session memory: {str(e)}", exc_info=True)
    
    # Also store directly under the step ID for reference variable compatibility
    try:
        session_manager.store_memory(session_id, current_step_id, {'response': user_response})
        logger.info(f"Stored response in session memory for step: {current_step_id}")
    except Exception as e:
        logger.error(f"Failed to store response in session memory: {str(e)}", exc_info=True)
    
    # Add the user's response to chat history
    try:
        session_manager.add_user_message(session_id, user_response)
        logger.info("Added user response to chat history")
    except Exception as e:
        logger.error(f"Failed to add user response to chat history: {str(e)}", exc_info=True)
    
    # Set the session status to active
    try:
        session_manager.set_session_status(session_id, 'active')
        logger.info("Set session status to active")
    except Exception as e:
        logger.error(f"Failed to set session status: {str(e)}", exc_info=True)
    
    # Try to continue the workflow automatically
    try:
        from core.graph_engine import get_graph_workflow_engine
        engine = get_graph_workflow_engine()
        engine.process_workflow_steps(session_id)
        logger.info("Continued workflow processing")
    except Exception as e:
        logger.error(f"Error continuing workflow after user response: {str(e)}", exc_info=True)
    
    return {'status': 'input_received'}
