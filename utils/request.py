import logging
from utils.store_memory import store_memory
from utils.resolve_variable import process_variables
import json

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
        session: The current session object to store results (legacy support)
        input_data: Dict containing:
            - statement: The question or statement to ask the user
            - query: Alternative name for statement
    
    Returns:
        A dict with status 'waiting_for_input' indicating a request has been initiated
    """
    # Extract the statement to show to the user
    # Support both 'statement' and 'query' parameter names
    statement = input_data.get('statement', input_data.get('query', 'What would you like to know?'))
    
    # Process any variable references in the statement
    if isinstance(statement, str) and '@{' in statement and 'id' in session:
        try:
            from engine import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver:
                # Use the new variable resolution
                statement = process_variables(driver, session['id'], statement)
        except (ImportError, AttributeError):
            # Fall back to legacy variable resolution
            pass
    
    # Get the current step ID, using proper naming for Neo4j
    # This is crucial for the workflow to find the data in the correct place
    current_step_id = "unknown"
    if 'current_step' in session and isinstance(session['current_step'], dict):
        current_step_id = session['current_step'].get('id', 'unknown')
    elif session.get('id', None):
        # For the new architecture, session['id'] refers to the session ID
        # We need to identify if we can extract the step ID from session data
        try:
            from engine import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver and 'id' in session:
                with driver.session() as db_session:
                    result = db_session.run("""
                        MATCH (s:SESSION {id: $session_id})
                        RETURN s.next_steps as next_steps
                    """, session_id=session['id'])
                    record = result.single()
                    if record and record['next_steps'] and len(record['next_steps']) > 0:
                        # The first item in next_steps should be the current step
                        current_step_id = record['next_steps'][0]
        except Exception as e:
            logger.warning(f"Failed to get current step ID from Neo4j: {str(e)}")
    
    logger.info(f"Using step ID: {current_step_id} for request storage")
    
    # Store this statement in the SESSION node memory
    try:
        from engine import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver and 'id' in session:
            # Store under both the request-stepId and the direct stepId
            # This ensures compatibility with how subsequent steps expect to find the data
            step_id_request = f"request-{current_step_id}"
            store_memory(driver, session['id'], step_id_request, {'statement': statement})
            
            # Also store directly under the step ID for reference variable compatibility
            store_memory(driver, session['id'], current_step_id, {'response': statement})
            
            # Update session status to awaiting_input
            with driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.status = 'awaiting_input'
                """, session_id=session['id'])
    except (ImportError, AttributeError, Exception) as e:
        logger.error(f"Error storing request in SESSION node: {str(e)}")
    
    # For backward compatibility with the old session approach
    session['request_statement'] = statement
    session['awaiting_input'] = True
    
    # Store a formatted message for the chat history
    if 'chat_history' not in session:
        session['chat_history'] = []
        
    session['chat_history'].append({
        'role': 'assistant',
        'content': statement
    })
    
    # Store chat history in SESSION node for new architecture
    try:
        from engine import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver and 'id' in session:
            with driver.session() as db_session:
                # Get current chat history
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.chat_history as chat_history
                """, session_id=session['id'])
                
                record = result.single()
                if record:
                    try:
                        # Parse current chat history
                        chat_history_str = record['chat_history'] if record['chat_history'] else "[]"
                        chat_history = json.loads(chat_history_str)
                        
                        # Add new message
                        chat_history.append({
                            'role': 'assistant',
                            'content': statement
                        })
                        
                        # Update chat history
                        db_session.run("""
                            MATCH (s:SESSION {id: $session_id})
                            SET s.chat_history = $chat_history
                        """, session_id=session['id'], chat_history=json.dumps(chat_history))
                        
                        logger.info(f"Updated chat history for session {session['id']}")
                    except Exception as e:
                        logger.error(f"Error parsing chat history: {str(e)}")
    except (ImportError, AttributeError, Exception) as e:
        logger.error(f"Error updating chat history in SESSION node: {str(e)}")
    
    # Return a flag indicating we're waiting for user input
    return {
        'status': 'waiting_for_input',
        'statement': statement
    }

def handle_user_response(session, user_response):
    """
    Handle the user's response to a request
    
    Args:
        session: The current session object
        user_response: The user's response text
        
    Returns:
        None, but updates the session
    """
    # Store the user's response in the session
    session['response'] = user_response
    
    # Mark the session as no longer awaiting input
    session['awaiting_input'] = False
    
    # Get the current step ID for proper storage
    current_step_id = "unknown"
    if 'current_step' in session and isinstance(session['current_step'], dict):
        current_step_id = session['current_step'].get('id', 'unknown')
    elif session.get('id', None):
        # For the new architecture, try to identify the current step
        try:
            from engine import get_neo4j_driver
            driver = get_neo4j_driver()
            if driver and 'id' in session:
                with driver.session() as db_session:
                    result = db_session.run("""
                        MATCH (s:SESSION {id: $session_id})
                        RETURN s.next_steps as next_steps
                    """, session_id=session['id'])
                    record = result.single()
                    if record and record['next_steps'] and len(record['next_steps']) > 0:
                        current_step_id = record['next_steps'][0]
        except Exception as e:
            logger.warning(f"Failed to get current step ID from Neo4j: {str(e)}")
    
    # If this is a follow-up to a question, store the question-answer pair for context
    if 'request_statement' in session:
        question = session.get('request_statement', '')
        
        # Track conversation context
        if 'conversation_context' not in session:
            session['conversation_context'] = []
            
        # Add the question-answer pair to context
        session['conversation_context'].append({
            'question': question,
            'answer': user_response
        })
        
        # Log that we're preserving context
        logger.info(f"Storing Q&A context: Question: '{question[:50]}...', Answer: '{user_response}'")
    
    # Store in SESSION node for the new architecture
    try:
        from engine import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver and 'id' in session:
            # Store under both response-stepId and directly in stepId for variable compatibility
            step_id_response = f"response-{current_step_id}"
            store_memory(driver, session['id'], step_id_response, {'response': user_response})
            
            # Also store directly under the step ID for reference variable compatibility
            store_memory(driver, session['id'], current_step_id, {'response': user_response})
            
            # Update session status to active
            with driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.status = 'active'
                """, session_id=session['id'])
            
            # Process the next steps
            # This is needed to ensure the workflow continues after handling input
            try:
                from graph_engine import get_graph_workflow_engine
                engine = get_graph_workflow_engine()
                engine.process_workflow_steps(session['id'])
            except (ImportError, AttributeError, Exception) as e:
                logger.error(f"Error continuing workflow after user response: {str(e)}")
    except (ImportError, AttributeError, Exception) as e:
        logger.error(f"Error storing response in SESSION node: {str(e)}")
    
    return {'status': 'input_received'}
