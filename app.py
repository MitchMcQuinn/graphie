import os
import json
import logging
import uuid
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO
from dotenv import load_dotenv
from graph_engine import get_graph_workflow_engine
from graphql_api import add_graphql_route

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

# Get the graph workflow engine
workflow_engine = get_graph_workflow_engine()

# Add GraphQL endpoint
add_graphql_route(app)

@app.route('/')
def index():
    """Render the chat interface"""
    # Generate a new session ID and store it in Flask session
    session.clear()
    session['id'] = str(uuid.uuid4())
    logger.info(f"Created new session with ID: {session['id']}")
    return render_template('index.html')

@app.route('/start_chat', methods=['POST'])
def start_chat():
    """Start a new chat session"""
    try:
        # Make sure we have a session ID
        if 'id' not in session:
            session['id'] = str(uuid.uuid4())
            logger.info(f"Created new session ID: {session['id']}")
        
        session_id = session['id']
        logger.info(f"Starting chat with session ID: {session_id}")
        
        # Start a new workflow with this session ID
        # This will create the session if it doesn't exist
        result = workflow_engine.start_workflow(session_id)
        logger.info(f"Workflow start result: {result}")
        
        # Get the current state from the engine
        frontend_state = workflow_engine.get_frontend_state(session_id)
        logger.info(f"Frontend state: {frontend_state}")
        
        return jsonify(frontend_state)
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}", exc_info=True)
        return jsonify({
            'awaiting_input': False,
            'error': True,
            'reply': f"There was an error starting the chat: {str(e)}"
        })

@app.route('/continue_processing', methods=['POST'])
def continue_processing():
    """Process the next steps in the workflow"""
    try:
        # Make sure we have a session ID
        if 'id' not in session:
            logger.error("No session ID found in /continue_processing")
            return jsonify({
                'awaiting_input': False,
                'error': True,
                'reply': "Session not found. Please refresh the page."
            })
        
        session_id = session['id']
        
        # Check if this session exists in the engine
        if not workflow_engine.has_session(session_id):
            logger.warning(f"Session {session_id} not found in engine, initializing new workflow")
            workflow_engine.start_workflow(session_id)
            return jsonify(workflow_engine.get_frontend_state(session_id))
        
        logger.info(f"Continuing processing for session {session_id}")
        
        # Let the engine process next steps
        workflow_engine.process_workflow_steps(session_id)
        
        # Get the current state from the engine
        return jsonify(workflow_engine.get_frontend_state(session_id))
    except Exception as e:
        logger.error(f"Error in continue_processing: {str(e)}", exc_info=True)
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
        
        # Get or create session ID
        if 'id' not in session:
            session['id'] = str(uuid.uuid4())
            logger.info(f"Created new session ID: {session['id']}")
        
        session_id = session['id']
        logger.info(f"Received message '{message}' for session {session_id}")
        
        # Check if this session exists in the engine
        if not workflow_engine.has_session(session_id):
            logger.warning(f"Session {session_id} not found in engine, initializing new workflow")
            workflow_engine.start_workflow(session_id)
        
        # Continue the workflow with the user's message
        result = workflow_engine.continue_workflow(message, session_id)
        logger.info(f"Continue workflow result: {result}")
        
        # Get the current state from the engine
        frontend_state = workflow_engine.get_frontend_state(session_id)
        logger.info(f"Frontend state: {frontend_state}")
        
        return jsonify(frontend_state)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return jsonify({
            'awaiting_input': False,
            'error': True,
            'reply': f"There was an error processing your message: {str(e)}"
        })

@app.route('/chat_history')
def chat_history():
    """Get the chat history"""
    if 'id' not in session:
        return jsonify([])
    
    session_id = session['id']
    history = workflow_engine.get_chat_history(session_id)
    return jsonify(history)

@app.route('/graphql-playground')
def graphql_playground():
    """Render the GraphQL Playground UI"""
    return render_template('graphql_playground.html')

if __name__ == '__main__':
    app.run(debug=True)
