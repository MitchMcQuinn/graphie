def request(session, input_data):
    """
    Human-in-the-loop request function that pauses the workflow until a user response is received.
    This function sets up the session to await user input, storing the question or statement
    to be displayed to the user in the front-end.
    
    Since Flask handles requests synchronously, this function doesn't actually block execution.
    Instead, it marks the session as awaiting input, which is checked by the workflow engine
    and API endpoints to pause processing until user input is received.
    
    Args:
        session: The current session object to store results
        input_data: Dict containing:
            - statement: The question or statement to ask the user
            - query: Alternative name for statement
    
    Returns:
        A dict with status 'waiting_for_input' indicating a request has been initiated
    """
    # Extract the statement to show to the user
    # Support both 'statement' and 'query' parameter names
    statement = input_data.get('statement', input_data.get('query', 'What would you like to know?'))
    
    # Store this statement in the session
    # This will be sent to the front-end to display to the user
    session['request_statement'] = statement
    
    # Mark the session as awaiting user input
    session['awaiting_input'] = True
    
    # Store a formatted message for the chat history
    if 'chat_history' not in session:
        session['chat_history'] = []
        
    session['chat_history'].append({
        'role': 'assistant',
        'content': statement
    })
    
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
    
    # Store the user's input in a standardized key for other functions to access
    session['user_input'] = user_response
    
    # Mark the session as no longer awaiting input
    session['awaiting_input'] = False
    
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Storing Q&A context: Question: '{question[:50]}...', Answer: '{user_response}'")
    
    return {'status': 'input_received'}
