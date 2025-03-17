import logging
import re
import json
from utils.store_memory import store_memory
from utils.resolve_variable import process_variables

logger = logging.getLogger(__name__)

def reply(session, input_data):
    """
    Simply forwards a response to the user in the chat window
    
    Args:
        session: The current session object to store results (legacy support)
        input_data: Dict containing:
            - response: The text to display to the user
            - or:
            - reply: The text to display to the user
    
    Returns:
        The reply that was sent
    """
    # This version of reply still supports the old session dict approach
    # while also working with the new architecture
    logger.info(f"Reply function received input_data: {input_data}")
    
    # Handle either 'response' or 'reply' field
    if 'response' in input_data:
        reply_text = input_data['response']
    else:
        reply_text = input_data.get('reply', '')
    
    # Process any variable references in the reply text
    if isinstance(reply_text, str):
        # If we're using the new architecture, this will already be processed
        # But we need to keep this for backward compatibility
        if '@{' in reply_text and 'id' in session:
            # Check if we can access the driver for variable resolution
            try:
                from engine import get_neo4j_driver
                driver = get_neo4j_driver()
                if driver:
                    # Handle SESSION_ID special variable
                    if 'SESSION_ID' in reply_text:
                        reply_text = reply_text.replace('SESSION_ID', session['id'])
                    
                    # Special handling for generate-answer.response
                    if '.generate-answer.response' in reply_text:
                        try:
                            with driver.session() as db_session:
                                result = db_session.run("""
                                    MATCH (s:SESSION {id: $session_id})
                                    RETURN s.memory as memory
                                """, session_id=session['id'])
                                
                                record = result.single()
                                if record and record['memory']:
                                    memory = json.loads(record['memory'])
                                    # Look for response in generate-answer
                                    if 'generate-answer' in memory and memory['generate-answer']:
                                        for output in reversed(memory['generate-answer']):
                                            if 'response' in output and isinstance(output['response'], str) and len(output['response']) > 20:
                                                reply_text = output['response']
                                                logger.info(f"Resolved generate-answer.response to: {reply_text[:50]}...")
                                                break
                        except Exception as e:
                            logger.error(f"Error resolving generate-answer.response: {str(e)}")
                    
                    # Use the new variable resolution for other variables
                    else:
                        reply_text = process_variables(driver, session['id'], reply_text)
            except (ImportError, AttributeError):
                # Fall back to legacy variable resolution
                pass
                
        # Legacy variable resolution (kept for backward compatibility)
        if '@{' in reply_text:
            # Check for variable references like @{step-id}.propertyname|defaultvalue
            var_pattern = re.compile(r'@\{([^}]+)\}')
            matches = var_pattern.findall(reply_text)
            
            if matches:
                for match in matches:
                    # Get the variable reference and any default value
                    parts = match.split('|', 1)
                    var_ref = parts[0].strip()
                    default_value = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Parse step-id and property name if it's in the format step-id.propertyname
                    if '.' in var_ref:
                        step_id, prop_name = var_ref.split('.', 1)
                        
                        # Check if step data exists in session
                        if step_id in session and prop_name in session[step_id]:
                            var_value = session[step_id][prop_name]
                            logger.info(f"Resolved variable @{{{var_ref}}} to: {var_value}")
                            reply_text = reply_text.replace(f"@{{{match}}}", str(var_value))
                        # Handle special case for nested properties like "generation.response"
                        elif step_id in session and "generation" in session[step_id] and "." in prop_name:
                            nested_props = prop_name.split(".")
                            if len(nested_props) == 2 and nested_props[0] in session[step_id] and nested_props[1] in session[step_id][nested_props[0]]:
                                var_value = session[step_id][nested_props[0]][nested_props[1]]
                                logger.info(f"Resolved nested variable @{{{var_ref}}} to: {var_value}")
                                reply_text = reply_text.replace(f"@{{{match}}}", str(var_value))
                            else:
                                logger.warning(f"Nested property @{{{var_ref}}} not found in session, using default")
                                reply_text = reply_text.replace(f"@{{{match}}}", default_value)
                        else:
                            logger.warning(f"Step property @{{{var_ref}}} not found in session, using default")
                            reply_text = reply_text.replace(f"@{{{match}}}", default_value)
                    else:
                        # Handle direct session variable reference (legacy support)
                        if var_ref in session:
                            var_value = session[var_ref]
                            logger.info(f"Resolved direct variable @{{{var_ref}}} to: {var_value}")
                            reply_text = reply_text.replace(f"@{{{match}}}", str(var_value))
                        else:
                            logger.warning(f"Direct variable @{{{var_ref}}} not found in session, using default")
                            reply_text = reply_text.replace(f"@{{{match}}}", default_value)
                
                logger.info(f"Reply text after variable substitution: {reply_text}")
    
    # If the reply is empty, provide a fallback
    if not reply_text or reply_text.startswith('.'):
        reply_text = "I'm sorry, I wasn't able to generate a proper response. Could you please try again?"
        logger.warning("Empty or invalid reply text, using fallback message")
    
    logger.info(f"Final reply text: {reply_text}")
    
    # Store this reply in the session
    # For the new architecture, store in SESSION node memory
    try:
        from engine import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver and 'id' in session:
            # Use the new store_memory function
            store_memory(driver, session['id'], f"reply-{session.get('current_step', {}).get('id', 'unknown')}", {'reply': reply_text})
    except (ImportError, AttributeError):
        # Fall back to legacy storage
        pass
    
    # For backward compatibility, still set these values
    session['last_reply'] = reply_text
    logger.info(f"Set session last_reply to: {reply_text}")
    
    # Make sure we're not waiting for input from the user
    # This is critical to ensure the workflow continues
    session['awaiting_input'] = False
    
    # Store a formatted message for the chat history
    if 'chat_history' not in session:
        session['chat_history'] = []
        
    session['chat_history'].append({
        'role': 'assistant',
        'content': reply_text
    })
    
    # Store chat history in SESSION node for new architecture
    try:
        from engine import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver and 'id' in session:
            with driver.session() as db_session:
                # First, get the current chat history
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.chat_history as chat_history
                """, session_id=session['id'])
                
                record = result.single()
                
                # Parse existing chat history or create a new one
                try:
                    if record and record['chat_history']:
                        chat_history = json.loads(record['chat_history'])
                    else:
                        chat_history = []
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid chat history JSON for session {session['id']}, resetting")
                    chat_history = []
                
                # Add the new message
                chat_history.append({
                    'role': 'assistant',
                    'content': reply_text
                })
                
                # Update the SESSION node with the new chat history
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.chat_history = $chat_history
                """, session_id=session['id'], chat_history=json.dumps(chat_history))
                
                logger.info(f"Updated chat history for session {session['id']}")
    except (ImportError, AttributeError, Exception) as e:
        logger.error(f"Error updating chat history in SESSION node: {str(e)}")
    
    return {
        'reply': reply_text
    }

# Alias for the reply function to match the Neo4j workflow
def respond(session, input_data):
    """
    Alias for the reply function to match the Neo4j workflow
    
    Args:
        session: The current session object to store results
        input_data: Dict containing:
            - response: The text to send to the user
    
    Returns:
        The response that was sent
    """
    return reply(session, input_data)
