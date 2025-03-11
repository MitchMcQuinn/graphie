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
        session.clear()  # Clear entire session to start fresh
        session['chat_history'] = []
        session['has_pending_steps'] = False
        
        # Start the workflow
        workflow_engine.start_workflow(session)
        
        # Process the first step of the workflow
        try:
            result = workflow_engine.process_current_step()
            
            # If we're waiting for input, send the request statement
            if session.get('awaiting_input', False):
                # Reset since we're waiting for user input
                session['has_pending_steps'] = False
                return jsonify({
                    'awaiting_input': True,
                    'statement': session.get('request_statement', 'What would you like to know?')
                })
            
            # If we have a reply to show from this step, send it with a flag indicating more steps
            if 'last_reply' in session:
                more_steps = workflow_engine.current_step is not None
                session['has_pending_steps'] = more_steps
                return jsonify({
                    'awaiting_input': False,
                    'reply': session.get('last_reply', ''),
                    'has_pending_steps': more_steps
                })
                
            # Continue processing steps until we need user input, find a reply, or complete
            return continue_processing()
                
        except Exception as e:
            logger.error(f"Error processing workflow step: {str(e)}")
            session['has_pending_steps'] = False  # Reset on error
            return jsonify({
                'awaiting_input': False,
                'error': True,
                'reply': f"There was an error processing the workflow: {str(e)}"
            })
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}", exc_info=True)
        session['has_pending_steps'] = False  # Reset on error
        return jsonify({
            'awaiting_input': False,
            'error': True,
            'reply': f"There was an error starting the chat: {str(e)}"
        })

@app.route('/continue_processing', methods=['POST'])
def continue_processing():
    """Continue processing the workflow after sending a reply to the frontend"""
    try:
        # Reset the last_reply so we don't keep returning the same one
        if 'last_reply' in session:
            prev_reply = session.pop('last_reply')
            logger.info(f"Cleared previous reply: {prev_reply[:50]}...")
        
        # Process workflow steps until we need user input, find a reply to show, or complete
        while True:
            try:
                # If no current step or workflow completed, break
                if not workflow_engine.current_step:
                    session['has_pending_steps'] = False
                    return jsonify({
                        'awaiting_input': False,
                        'reply': 'Workflow processing complete.',
                        'has_pending_steps': False
                    })
                    
                # Process the next step
                result = workflow_engine.process_current_step()
                
                # If we're waiting for input, send the request statement
                if session.get('awaiting_input', False):
                    session['has_pending_steps'] = False  # Reset since we're waiting for user input
                    return jsonify({
                        'awaiting_input': True,
                        'statement': session.get('request_statement', 'What would you like to know?')
                    })
                
                # If we have a reply to show, send it with a flag indicating more steps
                if 'last_reply' in session:
                    more_steps = workflow_engine.current_step is not None
                    session['has_pending_steps'] = more_steps
                    return jsonify({
                        'awaiting_input': False,
                        'reply': session.get('last_reply', ''),
                        'has_pending_steps': more_steps
                    })
                
                # If the workflow is complete or result is None, break
                if result is None or not workflow_engine.current_step:
                    session['has_pending_steps'] = False
                    if 'error' in session:
                        return jsonify({
                            'awaiting_input': False,
                            'error': True,
                            'reply': session.get('error', 'An unknown error occurred'),
                            'has_pending_steps': False
                        })
                    else:
                        return jsonify({
                            'awaiting_input': False,
                            'reply': 'Workflow processing complete.',
                            'has_pending_steps': False
                        })
            except Exception as e:
                logger.error(f"Error processing workflow step: {str(e)}")
                session['has_pending_steps'] = False  # Reset on error
                return jsonify({
                    'awaiting_input': False,
                    'error': True,
                    'reply': f"There was an error processing the workflow: {str(e)}"
                })
    except Exception as e:
        logger.error(f"Error continuing workflow: {str(e)}", exc_info=True)
        session['has_pending_steps'] = False  # Reset on error
        return jsonify({
            'awaiting_input': False,
            'error': True,
            'reply': f"There was an error continuing the workflow: {str(e)}"
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
                'reply': session['last_reply'],
                'has_pending_steps': False
            })
        
        # Reset has_pending_steps flag when processing new user input
        # This ensures we properly handle the new input rather than continuing old steps
        session['has_pending_steps'] = False
        
        # Continue the workflow with the user's input
        workflow_engine.continue_workflow(message)
        
        # Process the next step
        try:
            result = workflow_engine.process_current_step()
            
            # If we're waiting for input, send the request statement
            if session.get('awaiting_input', False):
                return jsonify({
                    'awaiting_input': True,
                    'statement': session.get('request_statement', 'What would you like to know?')
                })
            
            # If we have a reply to show, send it with a flag indicating more steps
            if 'last_reply' in session:
                more_steps = workflow_engine.current_step is not None
                session['has_pending_steps'] = more_steps
                response_data = {
                    'awaiting_input': False,
                    'reply': session.get('last_reply', ''),
                    'has_pending_steps': more_steps
                }
                logger.info(f"Returning response with reply and has_pending_steps={more_steps}")
                return jsonify(response_data)
            
            # Continue processing remaining steps
            return continue_processing()
                
        except Exception as e:
            logger.error(f"Error processing workflow step: {str(e)}")
            return jsonify({
                'awaiting_input': False,
                'error': True,
                'reply': f"There was an error processing the workflow: {str(e)}"
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
