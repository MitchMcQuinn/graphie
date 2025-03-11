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
    
    # Mark the session as no longer awaiting input
    session['awaiting_input'] = False
    
    return {'status': 'input_received'}
