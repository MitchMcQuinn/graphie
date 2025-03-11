import os
import json
import logging
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv
from engine import get_workflow_engine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Initialize SocketIO
socketio = SocketIO(app)

# Get the workflow engine
workflow_engine = get_workflow_engine()

@app.route('/')
def index():
    """Render the chat interface"""
    # Clear any existing session data
    session.clear()
    return render_template('index.html')

@app.route('/start_chat', methods=['POST'])
def start_chat():
    """Start a new chat session"""
    try:
        # Initialize session data
        session['chat_history'] = []
        
        # Start the workflow
        workflow_engine.start_workflow(session)
        
        # Process the workflow until we need user input or it completes
        while True:
            try:
                result = workflow_engine.process_current_step()
                
                # If we're waiting for input, send the request statement
                if session.get('awaiting_input', False):
                    return jsonify({
                        'awaiting_input': True,
                        'statement': session.get('request_statement', 'What would you like to know?')
                    })
                
                # If the workflow is complete (result is not None but no next step), break
                if result is not None and not workflow_engine.current_step:
                    logger.info("Workflow completed normally in start_chat")
                    break
                    
                # If something went wrong and result is None, break
                if result is None:
                    if 'error' not in session:
                        session['error'] = "Unknown error occurred during workflow processing"
                    break
            except Exception as e:
                logger.error(f"Error processing workflow step: {str(e)}")
                return jsonify({
                    'awaiting_input': False,
                    'error': True,
                    'reply': f"There was an error processing the workflow: {str(e)}"
                })
        
        # If we have a reply to show, send it
        if 'last_reply' in session:
            return jsonify({
                'awaiting_input': False,
                'reply': session.get('last_reply', '')
            })
        
        # If we have an error message, send it
        if 'error' in session:
            return jsonify({
                'awaiting_input': False,
                'error': True,
                'reply': session.get('error', 'An unknown error occurred')
            })
        
        # Default response
        return jsonify({
            'awaiting_input': False,
            'reply': 'Hello! How can I help you today?'
        })
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}", exc_info=True)
        return jsonify({
            'awaiting_input': False,
            'error': True,
            'reply': f"There was an error starting the chat: {str(e)}"
        })

@app.route('/send_message', methods=['POST'])
def send_message():
    """Handle a message from the user"""
    try:
        # Get the message from the request
        data = request.json
        message = data.get('message', '')
        
        # Add the message to the chat history
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        session['chat_history'].append({
            'role': 'user',
            'content': message
        })
        
        # Check if the workflow is already complete (no current step)
        if not workflow_engine.current_step:
            logger.info("Workflow already completed, sending end-of-session message")
            
            # Set a response for completed workflow
            session['last_reply'] = "We've reached the end of our session. Please refresh to start again."
            
            # Add the response to chat history
            session['chat_history'].append({
                'role': 'assistant',
                'content': session['last_reply']
            })
            
            return jsonify({
                'awaiting_input': False,
                'reply': session['last_reply']
            })
        
        # Continue the workflow with the user's input
        workflow_engine.continue_workflow(message)
        
        # Process the workflow until we need user input again or it completes
        while True:
            try:
                result = workflow_engine.process_current_step()
                
                # If we're waiting for input, send the request statement
                if session.get('awaiting_input', False):
                    return jsonify({
                        'awaiting_input': True,
                        'statement': session.get('request_statement', 'What would you like to know?')
                    })
                
                # If the workflow is complete (result is not None but no next step), break
                if result is not None and not workflow_engine.current_step:
                    logger.info("Workflow completed normally in send_message")
                    break
                    
                # If something went wrong and result is None, break
                if result is None:
                    if 'error' not in session:
                        session['error'] = "Unknown error occurred during workflow processing"
                    break
            except Exception as e:
                logger.error(f"Error processing workflow step: {str(e)}")
                return jsonify({
                    'awaiting_input': False,
                    'error': True,
                    'reply': f"There was an error processing the workflow: {str(e)}"
                })
        
        # Debug what's in the session
        logger.info(f"Session after workflow processing: last_reply = {session.get('last_reply', 'NOT FOUND')}")
        
        # If we have a reply to show, send it
        if 'last_reply' in session:
            response_data = {
                'awaiting_input': False,
                'reply': session.get('last_reply', '')
            }
            logger.info(f"Returning response with reply: {response_data['reply']}")
            return jsonify(response_data)
        
        # If we have an error message, send it
        if 'error' in session:
            return jsonify({
                'awaiting_input': False,
                'error': True,
                'reply': session.get('error', 'An unknown error occurred')
            })
        
        # Default response
        return jsonify({
            'awaiting_input': False,
            'reply': 'I processed your message, but I\'m not sure what to say next.'
        })
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}", exc_info=True)
        return jsonify({
            'awaiting_input': False,
            'error': True,
            'reply': f"There was an error processing your message: {str(e)}"
        })

@app.route('/chat_history')
def chat_history():
    """Get the chat history"""
    history = session.get('chat_history', [])
    return jsonify(history)

if __name__ == '__main__':
    app.run(debug=True)
