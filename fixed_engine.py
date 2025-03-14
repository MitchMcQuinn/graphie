import os
import json
import importlib
import re
import logging
from collections import deque
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

class PendingPath:
    """
    Represents a pending path in the workflow
    
    This class encapsulates a branch/path in the workflow
    that is waiting to be processed
    """
    
    def __init__(self, step, path_id=None):
        """
        Initialize a workflow path
        
        Args:
            step: The current step in this path
            path_id: Optional unique identifier for this path
        """
        self.current_step = step
        self.path_id = path_id or f"path_{id(self)}"
        
    def __str__(self):
        step_id = self.current_step.get('id', 'unknown') if self.current_step else 'None'
        return f"Path {self.path_id}: step={step_id}"

class FixedWorkflowEngine:
    def __init__(self):
        if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
            logger.error("Neo4j connection details are missing. Using mock engine.")
            self.driver = None
        else:
            try:
                self.driver = GraphDatabase.driver(
                    NEO4J_URL, 
                    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
                )
                # Test the connection
                with self.driver.session() as session:
                    session.run("RETURN 1")
                logger.info("Connected to Neo4j successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {str(e)}")
                self.driver = None
        
        # For compatibility with existing code
        self.current_step = None
        
        # For tracking pending paths
        self.pending_paths = []
        self.completed_paths = []
        self.max_parallel_paths = 5  # Maximum number of parallel paths to process per request
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def start_workflow(self, session_data):
        """
        Start a new workflow from the root node
        
        Args:
            session_data: The session object to store state
            
        Returns:
            The result of the first action, or None if waiting for input
        """
        # Clear any existing paths
        self.pending_paths = []
        self.completed_paths = []
        
        # Get the root node
        try:
            root_step = self._get_root_node()
            logger.info(f"Starting workflow with root node: {root_step.get('id')}")
            
            # Create the initial path
            initial_path = PendingPath(root_step, "root_path")
            
            # Add it to our pending paths
            self.pending_paths.append(initial_path)
            
            # Set the current step to the root for compatibility with existing code
            self.current_step = root_step
            
            # Process pending paths up to our limit
            return self.process_pending_paths(session_data)
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
            session_data['error'] = f"Error starting workflow: {str(e)}"
            return None
    
    def process_pending_paths(self, session_data):
        """
        Process pending paths up to our limit, all in the same thread
        
        Args:
            session_data: The session object to store state
            
        Returns:
            The result of the last processed path
        """
        result = None
        paths_processed = 0
        
        # Process paths up to our limit
        while self.pending_paths and paths_processed < self.max_parallel_paths:
            # Get the next pending path
            path = self.pending_paths.pop(0)
            
            # Set the current step for compatibility with existing code
            self.current_step = path.current_step
            
            try:
                # Process the step
                step_result = self._process_step(path.current_step, session_data)
                result = step_result  # Store the result
                
                # If we're awaiting input, add the path back to pending and stop processing
                if session_data.get('awaiting_input', False):
                    logger.info(f"Path {path.path_id} is awaiting user input at step {path.current_step.get('id')}")
                    self.pending_paths.insert(0, path)  # Put it back at the front
                    break
                
                # Get the next steps for this path
                next_steps = self._get_next_steps(path.current_step, session_data)
                
                if not next_steps:
                    # No next steps, mark this path as completed
                    logger.info(f"Path {path.path_id} completed at step {path.current_step.get('id')}")
                    self.completed_paths.append(path)
                else:
                    # Add new pending paths for each next step
                    for i, next_step in enumerate(next_steps):
                        new_path = PendingPath(
                            next_step, 
                            f"{path.path_id}_branch_{i}"
                        )
                        logger.info(f"Created new path {new_path.path_id} from {path.path_id} to step {next_step.get('id')}")
                        self.pending_paths.append(new_path)
            except Exception as e:
                logger.error(f"Error processing path {path.path_id}: {str(e)}", exc_info=True)
                session_data['error'] = f"Error processing path {path.path_id}: {str(e)}"
                self.completed_paths.append(path)
            
            paths_processed += 1
        
        return result
    
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
                "MATCH (n:STEP) WHERE n.id = 'root-2' RETURN n" # Set the root node here
            )
            record = result.single()
            if record:
                return dict(record['n'])
            else:
                raise Exception("Root node not found in the workflow")
    
    def process_current_step(self, session_data):
        """
        Process the current step in the workflow
        
        Args:
            session_data: The session object to store state
            
        Returns:
            The result of the action, or None if waiting for input
        """
        if not self.current_step:
            logger.info("No current step to process - workflow may be complete")
            return None
        
        return self._process_step(self.current_step, session_data)
    
    def _process_step(self, step, session_data):
        """
        Process a specific step in the workflow
        
        Args:
            step: The step to process
            session_data: The session object to store state
            
        Returns:
            The result of processing the step
        """
        current_step_id = step.get('id', 'unknown')
        logger.info(f"Processing step: {current_step_id}")
        
        # If this step has a function to execute
        if 'function' in step and step['function']:
            # Parse the function name (assuming module.function format)
            function_spec = step['function']
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
            if 'input' in step and step['input']:
                try:
                    input_data = json.loads(step['input'])
                    
                    # Process variable references in the input
                    input_data = self._process_variables(input_data, session_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing input JSON: {str(e)}")
                    session_data['error'] = f"Error parsing input JSON: {str(e)}"
                    return None
            
            # Import the module and get the function
            try:
                logger.info(f"Importing module {module_name} and function {function_name}")
                module = importlib.import_module(f"{module_name}")
                function = getattr(module, function_name)
            
                # Execute the function
                result = function(session_data, input_data)
                logger.info(f"Executed function {function_spec} for step {current_step_id}")
                
                # Debug what's in the session after the function call
                logger.info(f"After function execution, last_reply in session: {session_data.get('last_reply', 'NOT FOUND')}")
                
                # Return the result
                return result
            except Exception as e:
                logger.error(f"Error executing function {function_spec}: {str(e)}", exc_info=True)
                session_data['error'] = f"Error executing function {function_spec}: {str(e)}"
                return None
        else:
            # If there's no function, return a default result
            return True
    
    def _get_next_steps(self, current_step, session_data):
        """
        Get all valid next steps from the current step
        
        Args:
            current_step: The current step node
            session_data: The session object to store state
            
        Returns:
            List of valid next steps (may be empty)
        """
        if not current_step:
            logger.error("No current step to find next from")
            return []
        
        current_id = current_step.get('id', 'unknown')
        logger.info(f"Finding next steps from: {current_id}")
        
        if not self.driver:
            # Mock next step for demonstration
            if current_id == 'root':
                logger.warning("Using mock next step")
                return []
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (current:STEP {id: $id})-[r:NEXT]->(next:STEP)
                    RETURN next, r
                    """,
                    id=current_id
                )
                
                # Check if there are any next steps
                records = list(result)
                if not records:
                    logger.info(f"No NEXT relationships found from step {current_id}")
                    return []
                
                # Collect all valid next steps
                valid_next_steps = []
                
                for record in records:
                    relationship = dict(record['r'])
                    next_step = dict(record['next'])
                    next_id = next_step.get('id', 'unknown')
                    
                    # Check if the relationship has a condition function
                    if 'function' in relationship and relationship['function']:
                        logger.info(f"Evaluating condition for transition from {current_id} to {next_id}")
                        # Process the condition function
                        condition_result = self._process_condition(relationship, session_data)
                        if condition_result:
                            logger.info(f"Condition passed for transition to {next_id}")
                            valid_next_steps.append(next_step)
                        else:
                            logger.info(f"Condition failed for transition to {next_id}")
                    else:
                        # No condition, just add this step
                        logger.info(f"Adding unconditional transition to {next_id}")
                        valid_next_steps.append(next_step)
                
                return valid_next_steps
        except Exception as e:
            logger.error(f"Error getting next steps: {str(e)}", exc_info=True)
            return []
    
    def _process_condition(self, relationship, session_data):
        """
        Process a condition function in a NEXT relationship
        
        Args:
            relationship: Dict with the relationship properties
            session_data: The session object to store state
            
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
                input_data = self._process_variables(input_data, session_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing condition input JSON: {str(e)}")
                return False
        
        # Import the module and get the function
        try:
            logger.info(f"Importing module {module_name} and function {function_name} for condition")
            module = importlib.import_module(f"{module_name}")
            function = getattr(module, function_name)
            
            # Execute the function
            return function(session_data, input_data)
        except Exception as e:
            logger.error(f"Error executing condition function {function_spec}: {str(e)}")
            return False
    
    def _process_variables(self, data, session_data):
        """
        Process variable references in the input data
        
        Args:
            data: The input data with variables to process
            session_data: The session object to store state
            
        Returns:
            The processed data with variables replaced
        """
        if isinstance(data, dict):
            return {k: self._process_variables(v, session_data) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._process_variables(v, session_data) for v in data]
        elif isinstance(data, str):
            # Find variable references like @{node_id}.{key}
            return self._replace_variables(data, session_data)
        else:
            return data
    
    def _replace_variables(self, text, session_data):
        """
        Replace variable references in text with their values
        
        Args:
            text: The text with variables to replace
            session_data: The session object to store state
            
        Returns:
            The text with variables replaced
        """
        # Find all variable references with pattern @{node_id}.key or @{node_id}.key|default
        pattern = r'@\{([^}]+)\}\.(\w+)(?:\|([^@]*))?'
        
        # First, collect all matches (important to avoid modifying the string while iterating)
        matches = []
        for match in re.finditer(pattern, text):
            full_match = match.group(0)  # The entire matched text
            node_id = match.group(1)
            key = match.group(2)
            default_value = match.group(3) if match.lastindex >= 3 else None
            
            matches.append((full_match, node_id, key, default_value))
        
        # Log for debugging
        logger.info(f"Found variable references: {matches}")
        logger.info(f"Current session data keys: {list(session_data.keys())}")
        
        # Now process each match and replace in the text
        for full_match, node_id, key, default_value in matches:
            # Check if the key exists in session data
            if key in session_data:
                value = session_data[key]
                
                # If this is a JSON string (identified by being inside quotes), properly escape the value
                if '"' in text and ('"' + full_match in text or full_match + '"' in text):
                    # Use json.dumps to properly escape the value for JSON insertion
                    replacement = json.dumps(str(value))[1:-1]  # Remove the outer quotes from json.dumps
                    logger.info(f"JSON escaping and replacing '{full_match}' with value '{replacement}' from session")
                else:
                    replacement = str(value)
                    logger.info(f"Replacing '{full_match}' with value '{replacement}' from session")
            elif default_value is not None:
                # If this is a JSON string, properly escape the default value as well
                if '"' in text and ('"' + full_match in text or full_match + '"' in text):
                    replacement = json.dumps(default_value)[1:-1]
                    logger.info(f"JSON escaping and using default value '{replacement}' for variable @{{{node_id}}}.{key}")
                else:
                    replacement = default_value
                    logger.info(f"Variable @{{{node_id}}}.{key} not found in session data, using default value '{default_value}'")
            else:
                logger.warning(f"Variable @{{{node_id}}}.{key} not found in session data and no default provided")
                continue  # Skip this replacement
            
            # Replace the entire matched pattern with the replacement value
            text = text.replace(full_match, replacement)
        
        return text
    
    def continue_workflow(self, session_data, user_input=None):
        """
        Continue the workflow after user input
        
        Args:
            session_data: The session object to store state
            user_input: The user's input text
            
        Returns:
            The result of the next action, or None if waiting for more input
        """
        logger.info(f"Continuing workflow with user input: {user_input}")
        
        # Make sure we have a current step to continue from
        if not self.current_step:
            logger.warning("No current step, checking pending paths")
            if self.pending_paths:
                # Use the first pending path's step
                self.current_step = self.pending_paths[0].current_step
                logger.info(f"Using pending path step: {self.current_step.get('id')}")
            else:
                logger.warning("No pending paths, restarting from root")
                try:
                    self.current_step = self._get_root_node()
                    # Add it as a pending path
                    self.pending_paths = [PendingPath(self.current_step, "root_path")]
                except Exception as e:
                    logger.error(f"Failed to get root node: {str(e)}")
                    session_data['error'] = f"Error continuing workflow: {str(e)}"
                    return None
        
        # If we have user input, process it regardless of awaiting_input flag
        # This helps recover from session state inconsistencies
        if user_input is not None:
            logger.info("Processing user input response")
            
            try:
                # Store user_input in session data
                session_data['user_input'] = user_input
                
                # Add to chat history
                if 'chat_history' not in session_data:
                    session_data['chat_history'] = []
                
                session_data['chat_history'].append({
                    'role': 'user',
                    'content': user_input
                })
                
                # Mark as not awaiting input
                session_data['awaiting_input'] = False
                
                # Find the next steps from the current step
                if self.current_step:
                    current_id = self.current_step.get('id', 'unknown')
                    logger.info(f"Getting next steps after user input from step: {current_id}")
                    
                    # If we're at get-input, we need to transition to the next steps
                    if current_id == 'get-input':
                        # Get the next steps for the current path
                        next_steps = self._get_next_steps(self.current_step, session_data)
                        
                        if next_steps:
                            # Remove all existing pending paths since we're moving forward
                            self.pending_paths = []
                            
                            # Create new paths for each next step
                            for i, next_step in enumerate(next_steps):
                                new_path = PendingPath(
                                    next_step, 
                                    f"user_input_branch_{i}"
                                )
                                next_id = next_step.get('id', 'unknown')
                                logger.info(f"Created new path {new_path.path_id} from user input to step {next_id}")
                                self.pending_paths.append(new_path)
                        else:
                            logger.warning(f"No valid next steps found from {current_id} after user input")
                
                # Process pending paths to continue the workflow
                return self.process_pending_paths(session_data)
            except Exception as e:
                logger.error(f"Error handling user response: {str(e)}", exc_info=True)
                session_data['error'] = f"Error handling user response: {str(e)}"
                return None
        else:
            # No user input, just process pending paths
            logger.info("No user input provided, just processing pending paths")
            return self.process_pending_paths(session_data)
    
    def get_pending_path_count(self):
        """Get the number of pending paths"""
        return len(self.pending_paths)
    
    def get_path_statuses(self):
        """Get a summary of path statuses"""
        return {
            'pending': len(self.pending_paths),
            'completed': len(self.completed_paths),
            'pending_paths': [str(p) for p in self.pending_paths],
            'completed_paths': [str(p) for p in self.completed_paths]
        }

# Singleton instance of the workflow engine
_fixed_workflow_engine = None

def get_fixed_workflow_engine():
    """Get the singleton fixed workflow engine instance"""
    global _fixed_workflow_engine
    if _fixed_workflow_engine is None:
        _fixed_workflow_engine = FixedWorkflowEngine()
    return _fixed_workflow_engine 