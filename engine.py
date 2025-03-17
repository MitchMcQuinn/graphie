import os
import json
import importlib
import re
import logging
import uuid
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Check if Neo4j connection details are available
if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
    logger.warning("Neo4j connection details are missing. Please set NEO4J_URL, NEO4J_USERNAME, and NEO4J_PASSWORD in .env.local")

try:
    from neo4j import GraphDatabase
except ImportError:
    logger.error("Neo4j Python driver not installed. Please run 'pip install neo4j'")
    GraphDatabase = None

# Global Neo4j driver instance
_neo4j_driver = None

def get_neo4j_driver():
    """
    Get a Neo4j driver instance.
    
    Returns:
        A Neo4j driver instance or None if connection details are missing
    """
    global _neo4j_driver
    
    # Return existing driver if already initialized
    if _neo4j_driver is not None:
        return _neo4j_driver
    
    # Check if we have connection details
    if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
        logger.error("Neo4j connection details are missing. Cannot create driver.")
        return None
    
    # Initialize driver
    try:
        _neo4j_driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        # Test the connection
        with _neo4j_driver.session() as session:
            session.run("RETURN 1")
        logger.info("Connected to Neo4j successfully")
        return _neo4j_driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {str(e)}")
        return None

class WorkflowEngine:
    def __init__(self):
        self.driver = get_neo4j_driver()
        
        # Dictionary to store all session data by session ID
        self.sessions = {}
        # Current session ID being processed
        self.current_session_id = None
        # For backward compatibility
        self.session_data = {}
        self.current_step = None
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def _get_session_data(self, session_id):
        """Get session data for a given session ID, creating it if it doesn't exist"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'chat_history': [],
                'has_pending_steps': False,
                'awaiting_input': False
            }
        return self.sessions[session_id]
    
    def _set_current_session(self, session_id):
        """Set the current session being processed"""
        self.current_session_id = session_id
        self.session_data = self._get_session_data(session_id)
        # For backward compatibility, set current_step from the session
        self.current_step = self.session_data.get('current_step')
        return self.session_data
    
    def _save_current_step(self):
        """Save the current step to the session data"""
        if self.current_session_id:
            self.sessions[self.current_session_id]['current_step'] = self.current_step
    
    def start_workflow(self, session_id=None):
        """
        Start a new workflow from the root node
        
        Args:
            session_id: Session ID to use for this workflow
            
        Returns:
            The result of the first action, or None if waiting for input
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create a new session or reset an existing one
        self.sessions[session_id] = {
            'chat_history': [],
            'has_pending_steps': False,
            'awaiting_input': False
        }
        
        # Set as current session
        self._set_current_session(session_id)
        
        # Get the root node
        try:
            self.current_step = self._get_root_node()
            logger.info(f"Starting workflow with root node: {self.current_step.get('id')} for session {session_id}")
            
            # Save current step to session
            self._save_current_step()
            
            # Process the root node
            return self.process_current_step()
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
            self.session_data['error'] = f"Error starting workflow: {str(e)}"
            return None
    
    def has_session(self, session_id):
        """Check if a session exists"""
        return session_id in self.sessions
    
    def get_frontend_state(self, session_id=None):
        """
        Get the current state formatted for the frontend
        
        Args:
            session_id: Optional session ID to get state for, uses current if not provided
            
        Returns:
            Dict with state information for the frontend
        """
        # Use the current session if none specified
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        # Ensure we have a valid session ID
        if not session_id or session_id not in self.sessions:
            logger.error("No valid session ID provided for get_frontend_state")
            return {
                'error': True,
                'awaiting_input': False,
                'reply': "Session not found or invalid"
            }
        
        # Get the session data
        session_data = self.sessions[session_id]
        
        # Check for error
        if 'error' in session_data:
            return {
                'error': True,
                'awaiting_input': False,
                'reply': session_data['error']
            }
        
        # Check if awaiting input
        if session_data.get('awaiting_input', False):
            return {
                'awaiting_input': True,
                'statement': session_data.get('request_statement', 'What would you like to know?')
            }
        
        # Check if we have a reply
        if 'last_reply' in session_data:
            more_steps = session_data.get('current_step') is not None
            return {
                'awaiting_input': False,
                'reply': session_data.get('last_reply', ''),
                'has_pending_steps': more_steps,
                'structured_data': session_data.get('generation', {})
            }
        
        # Default response
        return {
            'awaiting_input': False,
            'reply': 'I processed your message, but I\'m not sure what to say next.',
            'has_pending_steps': session_data.get('current_step') is not None
        }
    
    def get_chat_history(self, session_id=None):
        """Get the chat history for a session"""
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        if not session_id or session_id not in self.sessions:
            return []
        
        return self.sessions[session_id].get('chat_history', [])
    
    def _get_root_node(self):
        """Get the root node of the workflow"""
        if not self.driver:
            # Mock root node for demonstration
            logger.warning("Using mock root node")
            return {
                'id': 'root',
                'description': 'Mock root node',
                'function': 'utils.reply.reply',
                'input': '{"reply": "Hello! This is a mock response since Neo4j is not configured."}'
            }
        
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n:STEP) WHERE n.id = 'root' RETURN n"
            )
            record = result.single()
            if record:
                return dict(record['n'])
            else:
                raise Exception("Root node not found in the workflow")
    
    def process_current_step(self):
        """
        Process the current step in the workflow
        
        Returns:
            The result of the action, or None if waiting for input
        """
        if not self.current_step:
            # This was raising an error, but if the workflow is complete,
            # this is expected and should not be treated as an error
            logger.info("No current step to process - workflow may be complete")
            return None
        
        current_step_id = self.current_step.get('id', 'unknown')
        logger.info(f"Processing step: {current_step_id}")
        
        # If this step has a function to execute
        if 'function' in self.current_step and self.current_step['function']:
            # Parse the function name (assuming module.function format)
            function_spec = self.current_step['function']
            if '.' in function_spec:
                parts = function_spec.split('.')
                if len(parts) == 2:
                    # If only one dot (e.g., "request.request"), assume it's from utils
                    module_name = f"utils.{parts[0]}"
                    function_name = parts[1]
                else:
                    # If multiple dots, use as is
                    module_name, function_name = function_spec.rsplit('.', 1)
            else:
                module_name = 'utils'
                function_name = function_spec
            
            # Parse the input JSON
            input_data = {}
            if 'input' in self.current_step and self.current_step['input']:
                try:
                    input_data = json.loads(self.current_step['input'])
                    
                    # Process variable references in the input
                    input_data = self._process_variables(input_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing input JSON: {str(e)}")
                    self.session_data['error'] = f"Error parsing input JSON: {str(e)}"
                    return None
            
            # Import the module and get the function
            try:
                logger.info(f"Importing module {module_name} and function {function_name}")
                module = importlib.import_module(f"{module_name}")
                function = getattr(module, function_name)
            
                # Execute the function
                result = function(self.session_data, input_data)
                logger.info(f"Executed function {function_spec} for step {current_step_id}")
                
                # Store the result in the session keyed by step ID for variable reference
                if result:
                    # Only store non-None results
                    if isinstance(result, dict):
                        # If the result is a dict, store it directly
                        self.session_data[current_step_id] = result
                        logger.info(f"Stored dict result in session under step ID: {current_step_id}")
                    else:
                        # For other types, wrap in a simple result object
                        self.session_data[current_step_id] = {'result': result}
                        logger.info(f"Stored non-dict result in session under step ID: {current_step_id}")
                
                # Add this line to debug what's in the session after the function call
                logger.info(f"After function execution, last_reply in session: {self.session_data.get('last_reply', 'NOT FOUND')}")
                logger.info(f"Session data for current step: {self.session_data.get(current_step_id, {})}")
                
                # If we're awaiting input, return None to indicate we should pause
                if self.session_data.get('awaiting_input', False):
                    logger.info(f"Step {current_step_id} is awaiting user input")
                    return None
                
                # Get the next step
                previous_step = self.current_step
                self._get_next_step()
                
                # Save the current step to the session
                self._save_current_step()
                
                if self.current_step:
                    logger.info(f"Moving from step {previous_step.get('id')} to {self.current_step.get('id')}")
                else:
                    logger.info(f"No next step after {previous_step.get('id')}, workflow complete")
                    logger.info("Workflow completed (no more steps)")
                
                # Return the result of this step - let the caller decide whether to continue processing
                return result
            except Exception as e:
                logger.error(f"Error executing function {function_spec}: {str(e)}", exc_info=True)
                self.session_data['error'] = f"Error executing function {function_spec}: {str(e)}"
                return None
        else:
            # If there's no function, just move to the next step
            previous_step = self.current_step
            self._get_next_step()
            
            # Save the current step to the session
            self._save_current_step()
            
            if self.current_step:
                logger.info(f"Moving from step {previous_step.get('id')} to {self.current_step.get('id')} (no function to execute)")
                # Return a default result to indicate the step was processed
                return True
            else:
                logger.info(f"No next step after {previous_step.get('id')}, workflow complete")
                logger.info("Workflow completed (no more steps)")
                return None
    
    def _get_next_step(self):
        """
        Get the next step in the workflow based on NEXT relationships
        """
        if not self.current_step:
            logger.error("No current step to find next from")
            return
        
        current_id = self.current_step['id']
        logger.info(f"Finding next step from: {current_id}")
        
        if not self.driver:
            # Mock next step for demonstration
            if current_id == 'root':
                logger.warning("Using mock next step")
                self.current_step = None
                return
        
        try:
            with self.driver.session() as session:
                query = """
                    MATCH (current:STEP {id: $id})-[r:NEXT]->(next:STEP)
                    RETURN next, r
                    """
                logger.info(f"Executing query: {query} with id={current_id}")
                
                result = session.run(query, id=current_id)
                
                # Check if there are any next steps
                records = list(result)
                logger.info(f"Found {len(records)} next steps")
                
                if not records:
                    logger.info(f"No NEXT relationships found from step {current_id}")
                    self.current_step = None
                    return
                
                # Get the first valid next step
                for record in records:
                    relationship = dict(record['r'])
                    next_step = dict(record['next'])
                    next_id = next_step.get('id', 'unknown')
                    logger.info(f"Found next step: {next_id} with relationship: {relationship}")
                    
                    # Check if the relationship has a condition function
                    if 'function' in relationship and relationship['function']:
                        logger.info(f"Evaluating condition for transition from {current_id} to {next_id}")
                        # Process the condition function
                        condition_result = self._process_condition(relationship)
                        if condition_result:
                            logger.info(f"Condition passed for transition to {next_id}")
                            self.current_step = next_step
                            return
                        else:
                            logger.info(f"Condition failed for transition to {next_id}")
                    else:
                        # No condition, just take this step
                        logger.info(f"Taking unconditional transition to {next_id}")
                        self.current_step = next_step
                        return
                
                # If we get here, there were no valid next steps
                logger.info(f"No valid next steps from {current_id}")
                self.current_step = None
        except Exception as e:
            logger.error(f"Error getting next step: {str(e)}", exc_info=True)
            self.current_step = None
    
    def _process_condition(self, relationship):
        """
        Process a condition function in a NEXT relationship
        
        Args:
            relationship: Dict with the relationship properties
            
        Returns:
            Boolean indicating if the condition is satisfied
        """
        # Parse the function name (assuming module.function format)
        function_spec = relationship['function']
        if '.' in function_spec:
            parts = function_spec.split('.')
            if len(parts) == 2:
                # If only one dot (e.g., "request.request"), assume it's from utils
                module_name = f"utils.{parts[0]}"
                function_name = parts[1]
            else:
                # If multiple dots, use as is
                module_name, function_name = function_spec.rsplit('.', 1)
        else:
            module_name = 'utils'
            function_name = function_spec
        
        # Parse the input JSON
        input_data = {}
        if 'input' in relationship and relationship['input']:
            try:
                input_data = json.loads(relationship['input'])
                
                # Process variable references in the input
                input_data = self._process_variables(input_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing condition input JSON: {str(e)}")
                return False
        
        # Import the module and get the function
        try:
            logger.info(f"Importing module {module_name} and function {function_name} for condition")
            module = importlib.import_module(f"{module_name}")
            function = getattr(module, function_name)
            
            # Execute the function
            return function(self.session_data, input_data)
        except Exception as e:
            logger.error(f"Error executing condition function {function_spec}: {str(e)}")
            return False
    
    def _process_variables(self, data):
        """
        Process variable references in the input data recursively
        
        Args:
            data: The input data with variables to process (can be dict, list, or primitive)
            
        Returns:
            The processed data with variables replaced
        """
        # Process dictionaries - recursively process each key-value pair
        if isinstance(data, dict):
            return {k: self._process_variables(v) for k, v in data.items()}
        
        # Process lists - recursively process each item
        elif isinstance(data, list):
            return [self._process_variables(v) for v in data]
        
        # Process strings - replace variables with their values
        elif isinstance(data, str):
            return self._replace_variables(data)
        
        # Return other data types as is
        else:
            return data
    
    def _replace_variables(self, text):
        """
        Replace variable references in text with their values
        
        Handles the pattern: @{step-id}.propertyname|defaultvalue
        Where:
        - step-id is the ID of a step that produced a result
        - propertyname is the property to access in that result
        - defaultvalue (optional) is used if the step or property doesn't exist
        
        Args:
            text: The text with variables to replace
            
        Returns:
            The text with variables replaced
        """
        # Nothing to process for non-string inputs
        if not isinstance(text, str):
            return text
        
        logger.info(f"Processing variable references in: {text}")
        
        # Use a regex pattern that captures the entire variable reference pattern
        # @{step-id}.propertyname|defaultvalue
        pattern = r'@\{([^}]+?)\}(?:\.([^|]+))?(?:\|(.+?))?(?=@\{|$)'
        
        # First, find all variable references in the text
        all_matches = list(re.finditer(r'@\{[^}]+\}(?:\.[^|@]+)?(?:\|[^@]+)?', text))
        
        # Process each match
        for match in all_matches:
            full_match = match.group(0)
            logger.info(f"Found full variable reference: {full_match}")
            
            # Parse the parts
            parts = re.match(r'@\{([^}]+)\}(?:\.([^|]+))?(?:\|(.+))?', full_match)
            if not parts:
                logger.warning(f"Failed to parse variable reference: {full_match}")
                continue
            
            step_id = parts.group(1).strip() if parts.group(1) else ""
            property_name = parts.group(2).strip() if parts.group(2) else None
            default_value = parts.group(3).strip() if parts.group(3) else ""
            
            logger.info(f"Parsed: step_id='{step_id}', property='{property_name}', default='{default_value}'")
            
            # Case 1: Step with property name
            if property_name and step_id in self.session_data:
                step_data = self.session_data[step_id]
                logger.info(f"Found step data for {step_id}: {step_data}")
                
                # Handle nested properties (e.g., generation.response)
                if isinstance(step_data, dict):
                    if '.' in property_name:
                        # Handle nested properties
                        prop_parts = property_name.split('.')
                        value = step_data
                        valid_path = True
                        
                        # Navigate through the nested structure
                        for part in prop_parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                logger.warning(f"Could not find nested property {part} in {step_id}")
                                valid_path = False
                                break
                        
                        if valid_path:
                            logger.info(f"Replaced {full_match} with value: {value}")
                            text = text.replace(full_match, str(value))
                        elif default_value:
                            logger.info(f"Using default value for {full_match}: {default_value}")
                            text = text.replace(full_match, default_value)
                    # Direct property access
                    elif property_name in step_data:
                        value = step_data[property_name]
                        logger.info(f"Replaced {full_match} with value: {value}")
                        text = text.replace(full_match, str(value))
                    elif default_value:
                        logger.info(f"Using default value for {full_match}: {default_value}")
                        text = text.replace(full_match, default_value)
                    else:
                        logger.warning(f"Property {property_name} not found in step {step_id}")
                elif default_value:
                    logger.info(f"Step data is not a dict, using default value: {default_value}")
                    text = text.replace(full_match, default_value)
                else:
                    logger.warning(f"Step data for {step_id} is not a dict and no default provided")
            
            # Case 2: Check if the entire step_id contains a dot (might be a malformed property access)
            elif '.' in step_id and not property_name:
                actual_step_id, actual_property = step_id.split('.', 1)
                logger.info(f"Trying alternative parsing: step_id='{actual_step_id}', property='{actual_property}'")
                
                if actual_step_id in self.session_data:
                    step_data = self.session_data[actual_step_id]
                    
                    if isinstance(step_data, dict) and actual_property in step_data:
                        value = step_data[actual_property]
                        logger.info(f"Replaced {full_match} with value: {value}")
                        text = text.replace(full_match, str(value))
                    elif isinstance(step_data, dict) and '.' in actual_property:
                        # Try nested property access
                        prop_parts = actual_property.split('.')
                        value = step_data
                        valid_path = True
                        
                        for part in prop_parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                valid_path = False
                                break
                        
                        if valid_path:
                            logger.info(f"Replaced {full_match} with nested value: {value}")
                            text = text.replace(full_match, str(value))
                        elif default_value:
                            logger.info(f"Using default value for {full_match}: {default_value}")
                            text = text.replace(full_match, default_value)
                    elif default_value:
                        logger.info(f"Property not found, using default value: {default_value}")
                        text = text.replace(full_match, default_value)
                
            # Case 3: Direct variable reference or use default
            elif step_id in self.session_data and not property_name:
                value = self.session_data[step_id]
                if isinstance(value, (str, int, float, bool)):
                    logger.info(f"Replaced {full_match} with value: {value}")
                    text = text.replace(full_match, str(value))
                elif 'result' in value and isinstance(value, dict):
                    logger.info(f"Replaced {full_match} with result value: {value['result']}")
                    text = text.replace(full_match, str(value['result']))
                elif default_value:
                    logger.info(f"Complex value, using default value: {default_value}")
                    text = text.replace(full_match, default_value)
            
            # Case 4: Default value
            elif default_value:
                logger.info(f"Using default value for {full_match}: {default_value}")
                text = text.replace(full_match, default_value)
            else:
                logger.warning(f"Could not resolve {full_match} and no default value provided")
                # In this case, we'll leave the original text unchanged
        
        logger.info(f"After variable replacement: {text}")
        return text
    
    def continue_workflow(self, user_input=None, session_id=None):
        """
        Continue the workflow after user input
        
        Args:
            user_input: The user's input text
            session_id: The session ID to continue
            
        Returns:
            The result of the next action, or None if waiting for more input
        """
        # Set the current session if provided
        if session_id:
            self._set_current_session(session_id)
        
        logger.info(f"Continuing workflow with user input: {user_input} for session {self.current_session_id}")
        
        # Add the user message to chat history
        if user_input and 'chat_history' in self.session_data:
            self.session_data['chat_history'].append({
                'role': 'user',
                'content': user_input
            })
        
        # Make sure we have a current step to continue from
        if not self.current_step and self.session_data.get('awaiting_input', False):
            logger.warning("No current step but awaiting input, restarting from root")
            try:
                self.current_step = self._get_root_node()
                # Save the current step to the session
                self._save_current_step()
            except Exception as e:
                logger.error(f"Failed to get root node: {str(e)}")
                self.session_data['error'] = f"Error continuing workflow: {str(e)}"
                return None
        
        # If we were awaiting input, process it
        if self.session_data.get('awaiting_input', False) and user_input is not None:
            logger.info("Processing user input response")
            
            # Store the current step ID before processing the input
            current_id = self.current_step.get('id') if self.current_step else None
            
            # Import the request module to handle the user's response
            try:
                from utils.request import handle_user_response
                handle_user_response(self.session_data, user_input)
                logger.info(f"User response handled. Current input awaiting flag: {self.session_data.get('awaiting_input', False)}")
                
                # Since we've processed the input, get the next step
                self._get_next_step()
                
                # Save the current step to the session
                self._save_current_step()
                
                # Log the transition
                next_id = self.current_step.get('id') if self.current_step else None
                logger.info(f"Transitioned from {current_id} to {next_id} after user input")
                
                # If we couldn't get a next step, this is a problem
                if not self.current_step:
                    error_msg = f"No next step found after processing user input from {current_id}"
                    logger.error(error_msg)
                    self.session_data['error'] = error_msg
                    return None
            except Exception as e:
                logger.error(f"Error handling user response: {str(e)}", exc_info=True)
                self.session_data['error'] = f"Error handling user response: {str(e)}"
                return None
        else:
            if not self.current_step:
                # This is not an error if we've completed the workflow
                logger.info("No current step to continue from - workflow may be complete")
                return None
            
            if not self.session_data.get('awaiting_input', False) and user_input is not None:
                logger.warning(f"Received user input but not awaiting input. Current step: {self.current_step.get('id')}")
        
        # Only continue processing if we have a current step
        if not self.current_step:
            logger.info("Workflow already completed, no more steps to process")
            return None
        
        # Continue processing steps
        return self.process_current_step()

# Singleton instance of the workflow engine
_workflow_engine = None

def get_workflow_engine():
    """Get the singleton workflow engine instance"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine

# Add a property to access the session mapping directly
def get_sessions():
    """Get the sessions dictionary from the workflow engine"""
    engine = get_workflow_engine()
    return engine.sessions

# Add a function to check if a session exists
def has_session(session_id):
    """Check if a session exists in the workflow engine"""
    engine = get_workflow_engine()
    return engine.has_session(session_id)
