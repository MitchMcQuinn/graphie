import os
import json
import logging
from flask import Flask, render_template, request, session, jsonify, redirect, url_for, Response
from flask_socketio import SocketIO
from dotenv import load_dotenv
from synced_engine import get_synced_workflow_engine

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

# Get the workflow engine with a retry delay of 0.5 seconds
workflow_engine = get_synced_workflow_engine(max_parallel_paths=5, retry_delay=0.5)

@app.route('/')
def index():
    """Render the chat interface"""
    # Clear any existing session data
    session.clear()
    
    # Mark any previous sessions as inactive
    workflow_engine.mark_session_inactive()
    
    # Reset active status for the new session
    workflow_engine.session_active = True
    
    return render_template('index.html')

@app.route('/start_chat', methods=['POST'])
def start_chat():
    """Start a new chat session"""
    try:
        # Initialize session data
        session.clear()  # Clear entire session to start fresh
        session['chat_history'] = []
        
        # Mark any previous sessions as inactive and set this one as active
        workflow_engine.mark_session_inactive()
        workflow_engine.session_active = True
        
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
                'has_pending_steps': workflow_engine.get_pending_path_count() > 0 or len(workflow_engine.deferred_steps) > 0
            })
            
        # If we don't have a reply yet, see if we should continue processing
        if workflow_engine.get_pending_path_count() > 0 or len(workflow_engine.deferred_steps) > 0:
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
            has_pending = workflow_engine.get_pending_path_count() > 0 or len(workflow_engine.deferred_steps) > 0
            return jsonify({
                'awaiting_input': False,
                'reply': session.get('last_reply', ''),
                'has_pending_steps': has_pending,
                'deferred_count': len(workflow_engine.deferred_steps)
            })
        
        # If there are still more paths to process or deferred steps
        has_pending = workflow_engine.get_pending_path_count() > 0 or len(workflow_engine.deferred_steps) > 0
        if has_pending:
            # Check if we have deferred steps with missing variables
            if len(workflow_engine.deferred_steps) > 0:
                waiting_for = []
                for key, info in workflow_engine.deferred_steps.items():
                    step = info['step']
                    waiting_for.append(f"{step.get('id', 'unknown')} (attempts: {info['attempts']})")
                
                return jsonify({
                    'awaiting_input': False,
                    'reply': f"Processing... Waiting for variables to be available for steps: {', '.join(waiting_for)}",
                    'has_pending_steps': True,
                    'deferred_count': len(workflow_engine.deferred_steps)
                })
            else:
                return jsonify({
                    'awaiting_input': False,
                    'reply': 'Processing...',
                    'has_pending_steps': True,
                    'deferred_count': 0
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
        if workflow_engine.get_pending_path_count() == 0 and len(workflow_engine.deferred_steps) == 0:
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
            
            # Mark this session as active
            workflow_engine.session_active = True
            
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
            has_pending = workflow_engine.get_pending_path_count() > 0 or len(workflow_engine.deferred_steps) > 0
            logger.info(f"Returning response with reply and has_pending_steps={has_pending}")
            return jsonify({
                'awaiting_input': False,
                'reply': session.get('last_reply', ''),
                'has_pending_steps': has_pending,
                'deferred_count': len(workflow_engine.deferred_steps)
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
    deferred_steps = workflow_engine.get_deferred_steps_info()
    
    # Get all variables from session
    variables = {}
    for key in session.keys():
        try:
            # Convert to string representation safely
            if isinstance(session[key], (dict, list)):
                variables[key] = f"[Complex type with {len(session[key])} items]"
            else:
                variables[key] = str(session[key])
        except:
            variables[key] = "ERROR: Could not convert to string"
    
    return jsonify({
        'path_statuses': path_statuses,
        'deferred_steps': deferred_steps,
        'session_keys': list(session.keys()),
        'session_variables': variables,
        'has_last_reply': 'last_reply' in session,
        'awaiting_input': session.get('awaiting_input', False),
        'is_session_active': workflow_engine.session_active
    })

@app.route('/debug_variables')
def debug_variables():
    """Debug endpoint to check variable availability"""
    all_variables = {}
    waiting_for = {}
    
    # List all variables in the session
    for key in session.keys():
        try:
            all_variables[key] = str(session[key])[:100]  # Truncate long values
        except:
            all_variables[key] = "ERROR: Could not convert to string"
    
    # Check what variables deferred steps are waiting for
    for step_key, info in workflow_engine.deferred_steps.items():
        step = info['step']
        step_id = step.get('id', 'unknown')
        
        if 'input' in step and step['input']:
            # Extract variable references
            pattern = r'@\{([^}]+)\}\.(\w+)'
            try:
                input_data = step['input']
                if isinstance(input_data, str):
                    input_data = json.loads(input_data)
                input_str = json.dumps(input_data)
                
                missing = []
                for match in re.finditer(pattern, input_str):
                    node_id = match.group(1)
                    key = match.group(2)
                    if key not in session:
                        missing.append(f"@{{{node_id}}}.{key}")
                
                if missing:
                    waiting_for[step_id] = {
                        'attempts': info['attempts'],
                        'missing_variables': missing
                    }
            except Exception as e:
                logger.error(f"Error extracting variables for step {step_id}: {str(e)}")
                waiting_for[step_id] = {
                    'attempts': info['attempts'],
                    'error': str(e)
                }
    
    return jsonify({
        'available_variables': all_variables,
        'waiting_for': waiting_for,
        'session_active': workflow_engine.session_active
    })

@app.route('/stream_log')
def stream_log():
    """Stream log events to the browser for debugging"""
    def generate():
        # Set up a custom handler to capture logs
        log_queue = []
        
        class QueueHandler(logging.Handler):
            def emit(self, record):
                log_entry = self.format(record)
                log_queue.append(log_entry)
        
        # Add the handler to the logger
        queue_handler = QueueHandler()
        queue_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        
        try:
            while True:
                if log_queue:
                    log_entry = log_queue.pop(0)
                    yield f"data: {log_entry}\n\n"
                else:
                    yield f"data: HEARTBEAT\n\n"
                    
                import time
                time.sleep(0.5)
        finally:
            # Remove the handler when the client disconnects
            root_logger.removeHandler(queue_handler)
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Use a different port to avoid conflict with the original app 