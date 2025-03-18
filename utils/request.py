import logging
import json
from utils.session_manager import get_session_manager
from utils.resolve_variable import process_variables
from utils.database import get_neo4j_driver

logger = logging.getLogger(__name__)

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
    
    # Extract the statement to show to the user
    # Support both 'statement' and 'query' parameter names
    statement = input_data.get('statement', input_data.get('query', 'What would you like to know?'))
    
    # Process any variable references in the statement
    if isinstance(statement, str) and '@{' in statement:
        statement = process_variables(driver, session_id, statement)
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    try:
        status = session_manager.get_session_status(session_id)
        if 'next_steps' in status and status['next_steps'] and len(status['next_steps']) > 0:
            current_step_id = status['next_steps'][0]
    except Exception as e:
        logger.warning(f"Failed to get current step ID: {str(e)}")
    
    logger.info(f"Using step ID: {current_step_id} for request storage")
    
    # Store the statement in session memory
    step_id_request = f"request-{current_step_id}"
    session_manager.store_memory(session_id, step_id_request, {'statement': statement})
    
    # Also store directly under the step ID for reference variable compatibility
    session_manager.store_memory(session_id, current_step_id, {'response': statement})
    
    # Set the session status to awaiting input
    session_manager.set_session_status(session_id, 'awaiting_input')
    
    # Add the statement to chat history
    session_manager.add_assistant_message(session_id, statement)
    
    logger.info(f"Request function completed for session {session_id}, statement: {statement}")
    
    # Return a flag indicating we're waiting for user input
    return {
        'status': 'waiting_for_input',
        'statement': statement
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
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    try:
        status = session_manager.get_session_status(session_id)
        if 'next_steps' in status and status['next_steps'] and len(status['next_steps']) > 0:
            current_step_id = status['next_steps'][0]
    except Exception as e:
        logger.warning(f"Failed to get current step ID: {str(e)}")
    
    logger.info(f"Handling user response for session {session_id}, step: {current_step_id}")
    
    # Store the user's response in session memory
    step_id_response = f"response-{current_step_id}"
    session_manager.store_memory(session_id, step_id_response, {'response': user_response})
    
    # Also store directly under the step ID for reference variable compatibility
    session_manager.store_memory(session_id, current_step_id, {'response': user_response})
    
    # Add the user's response to chat history
    session_manager.add_user_message(session_id, user_response)
    
    # Set the session status to active
    session_manager.set_session_status(session_id, 'active')
    
    # Try to continue the workflow automatically
    try:
        from graph_engine import get_graph_workflow_engine
        engine = get_graph_workflow_engine()
        engine.process_workflow_steps(session_id)
    except Exception as e:
        logger.error(f"Error continuing workflow after user response: {str(e)}")
    
    return {'status': 'input_received'}
