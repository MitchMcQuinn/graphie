import os
import json
import logging
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv
from fixed_engine import get_fixed_workflow_engine

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
workflow_engine = get_fixed_workflow_engine()

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
        
        # Start the workflow by processing the root node and its paths
        workflow_engine.start_workflow(session)
        
        # If we're waiting for input, send the request statement
        if session.get('awaiting_input', False):
            return jsonify({
                'awaiting_input': True,
                'statement': session.get('request_statement', 'What would you like to know?')
            })
        
        # If we have a reply to show from this step, send it
        if 'last_reply' in session:
            return jsonify({
                'awaiting_input': False,
                'reply': session.get('last_reply', ''),
                'has_pending_steps': workflow_engine.get_pending_path_count() > 0
            })
            
        # If we don't have a reply yet, see if we should continue processing
        if workflow_engine.get_pending_path_count() > 0:
            return continue_processing()
        else:
            # No more paths to process
            return jsonify({
                'awaiting_input': False,
                'reply': 'Workflow processing complete.',
                'has_pending_steps': False
            })
                
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}", exc_info=True)
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
        
        # Process more pending paths
        workflow_engine.process_pending_paths(session)
        
        # If we're waiting for input, send the request statement
        if session.get('awaiting_input', False):
            return jsonify({
                'awaiting_input': True,
                'statement': session.get('request_statement', 'What would you like to know?')
            })
        
        # If we have a reply to show, send it
        if 'last_reply' in session:
            return jsonify({
                'awaiting_input': False,
                'reply': session.get('last_reply', ''),
                'has_pending_paths': workflow_engine.get_pending_path_count() > 0
            })
        
        # If there are still more paths to process, but no reply yet
        if workflow_engine.get_pending_path_count() > 0:
            return jsonify({
                'awaiting_input': False,
                'reply': 'Processing...',
                'has_pending_steps': True
            })
            
        # No more paths to process
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
        logger.error(f"Error continuing workflow: {str(e)}", exc_info=True)
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
        
        # No pending paths to continue with this message
        if workflow_engine.get_pending_path_count() == 0:
            logger.info("No pending paths, starting new workflow with user input")
            
            # Check if we're at the end of our workflow
            path_statuses = workflow_engine.get_path_statuses()
            if path_statuses['completed'] > 0 and path_statuses['pending'] == 0:
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
            
            # Start a new workflow with this input
            workflow_engine.start_workflow(session)
        else:
            # Continue with existing workflow
            logger.info("Continuing workflow with user input")
            workflow_engine.continue_workflow(session, message)
        
        # If we're waiting for input, send the request statement
        if session.get('awaiting_input', False):
            return jsonify({
                'awaiting_input': True,
                'statement': session.get('request_statement', 'What would you like to know?')
            })
        
        # If we have a reply to show, send it
        if 'last_reply' in session:
            has_pending = workflow_engine.get_pending_path_count() > 0
            logger.info(f"Returning response with reply and has_pending_steps={has_pending}")
            return jsonify({
                'awaiting_input': False,
                'reply': session.get('last_reply', ''),
                'has_pending_steps': has_pending
            })
        
        # Continue processing remaining steps
        return continue_processing()
                
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

@app.route('/debug_workflow')
def debug_workflow():
    """Debug endpoint to see the current workflow state"""
    path_statuses = workflow_engine.get_path_statuses()
    
    return jsonify({
        'path_statuses': path_statuses,
        'session_keys': list(session.keys()),
        'has_last_reply': 'last_reply' in session,
        'awaiting_input': session.get('awaiting_input', False),
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Use a different port to avoid conflict with the original app 