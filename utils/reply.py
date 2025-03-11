def reply(session, input_data):
    """
    Simply forwards a response to the user in the chat window
    
    Args:
        session: The current session object to store results
        input_data: Dict containing:
            - reply: The text to send to the user
    
    Returns:
        The reply that was sent
    """
    # Extract the reply to send to the user
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Reply function received input_data: {input_data}")
    
    # Check if we received an unprocessed variable reference
    if 'response' in input_data and isinstance(input_data['response'], str):
        response_text = input_data['response']
        
        # Check if it's an unprocessed variable reference to generation
        if '@{generate-answer}.generation' in response_text:
            logger.info("Detected unprocessed variable reference to generation")
            
            # Try to get the generation directly from session
            if 'generation' in session:
                logger.info(f"Using generation from session: {session['generation']}")
                input_data['reply'] = session['generation']
            else:
                # Fallback to a default message if generation is missing
                logger.warning("Generation not found in session, using fallback message")
                input_data['reply'] = "I'm sorry, I wasn't able to generate a proper response. Could you please try again?"
        else:
            # Just convert response to reply
            input_data['reply'] = response_text
    
    # If we still don't have a reply, extract it from input_data
    if 'reply' not in input_data:
        reply_text = input_data.get('reply', '')
    else:
        reply_text = input_data['reply']
    
    logger.info(f"Final reply text: {reply_text}")
    
    # Store this reply in the session
    # This will be sent to the front-end to display to the user
    session['last_reply'] = reply_text
    logger.info(f"Set session last_reply to: {reply_text}")
    
    # Store a formatted message for the chat history
    if 'chat_history' not in session:
        session['chat_history'] = []
        
    session['chat_history'].append({
        'role': 'assistant',
        'content': reply_text
    })
    
    return reply_text

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
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Reply function received input_data: {input_data}")
    
    # Check if we received an unprocessed variable reference
    if 'response' in input_data and isinstance(input_data['response'], str):
        response_text = input_data['response']
        
        # Check if it's an unprocessed variable reference to generation
        if '@{generate-answer}.generation' in response_text:
            logger.info("Detected unprocessed variable reference to generation")
            
            # Try to get the generation directly from session
            if 'generation' in session:
                logger.info(f"Using generation from session: {session['generation']}")
                input_data['response'] = session['generation']
            else:
                # Fallback to a default message if generation is missing
                logger.warning("Generation not found in session, using fallback message")
                input_data['response'] = "I'm sorry, I wasn't able to generate a proper response. Could you please try again?"
    
    # Rename 'response' to 'reply' for the reply function
    if 'response' in input_data:
        input_data['reply'] = input_data.pop('response')
    
    logger.info(f"Processed input data: {input_data}")
    return reply(session, input_data)
