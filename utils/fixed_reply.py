import logging

# Set up logging
logger = logging.getLogger(__name__)

def fixed_reply(session, input_data):
    """
    Modified version of reply function that safely handles session updates
    without assuming Flask context
    
    Args:
        session: The current session-like object to store results
        input_data: Dict containing:
            - reply: The text to send to the user
    
    Returns:
        The reply that was sent
    """
    # Extract the reply to send to the user
    logger.info(f"Fixed reply function received input_data: {input_data}")
    
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
        reply_text = "I don't have a specific reply to share right now."
    else:
        reply_text = input_data['reply']
    
    logger.info(f"Final reply text: {reply_text}")
    
    try:
        # Safely update the session with the reply
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
    except Exception as e:
        # If we can't update the session directly, just log it
        # This could happen if we're in a background thread
        logger.error(f"Error updating session: {str(e)}")
        # But still return the reply text so the caller can handle it
    
    return reply_text

# Alias for the reply function to match the Neo4j workflow
def fixed_respond(session, input_data):
    """
    Alias for the fixed_reply function to match the Neo4j workflow
    
    Args:
        session: The current session object to store results
        input_data: Dict containing:
            - response: The text to send to the user
    
    Returns:
        The response that was sent
    """
    logger.info(f"Fixed respond function received input_data: {input_data}")
    
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
    
    # Call the fixed_reply function
    return fixed_reply(session, input_data) 