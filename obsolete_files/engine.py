import os
import json
import importlib
import re
import logging
import threading
import time
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

class WorkflowPath:
    """
    Represents a single path in the workflow
    
    This class encapsulates a branch/path in the workflow
    and its associated state (current step, local data)
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
        self.status = "pending"  # pending, running, completed, error
        self.error = None
        self.is_active = True
        
    def __str__(self):
        step_id = self.current_step.get('id', 'unknown') if self.current_step else 'None'
        return f"Path {self.path_id}: step={step_id}, status={self.status}"

class WorkflowEngine:
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
        
        self.current_step = None
        self.session_data = {}
        
        # For parallel processing
        self.paths = []
        self.completed_paths = []
        self.path_lock = threading.RLock()
        self.max_parallel_paths = 5  # Maximum number of parallel paths to process
        self.results = {}  # Store results from each path
        
        # Background processing thread
        self.processing_thread = None
        self.should_stop = False
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def start_workflow(self, session_data=None):
        """
        Start a new workflow from the root node
        
        Args:
            session_data: Optional initial session data
            
        Returns:
            The result of the first action, or None if waiting for input
        """
        if session_data:
            self.session_data = session_data
        else:
            self.session_data = {}
        
        # Clear any existing paths
        with self.path_lock:
            self.paths = []
            self.completed_paths = []
            self.results = {}
        
        # Get the root node
        try:
            root_step = self._get_root_node()
            logger.info(f"Starting workflow with root node: {root_step.get('id')}")
            
            # Create the initial path
            initial_path = WorkflowPath(root_step, "root_path")
            
            # Add it to our paths
            with self.path_lock:
                self.paths.append(initial_path)
            
            # Set the current step to the root for compatibility with existing code
            self.current_step = root_step
            
            # Start the background processing thread if not already running
            self._ensure_processing_thread()
            
            # Process the root node (compatibility with existing code)
            return self.process_current_step()
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
            self.session_data['error'] = f"Error starting workflow: {str(e)}"
            return None
    
    def _ensure_processing_thread(self):
        """Ensure the background processing thread is running"""
        if not self.processing_thread or not self.processing_thread.is_alive():
            logger.info("Starting background workflow processing thread")
            self.should_stop = False
            self.processing_thread = threading.Thread(
                target=self._process_paths_background, 
                daemon=True
            )
            self.processing_thread.start()
    
    def _process_paths_background(self):
        """Background thread to process workflow paths"""
        while not self.should_stop:
            try:
                # Get a list of pending paths to process
                paths_to_process = []
                with self.path_lock:
                    # Only process up to max_parallel_paths
                    active_count = sum(1 for p in self.paths if p.status == "running")
                    remaining = self.max_parallel_paths - active_count
                    
                    if remaining > 0:
                        # Get pending paths
                        pending_paths = [p for p in self.paths if p.status == "pending" and p.is_active]
                        paths_to_process = pending_paths[:remaining]
                        
                        # Mark them as running
                        for path in paths_to_process:
                            path.status = "running"
                
                # Process each path in a separate thread
                threads = []
                for path in paths_to_process:
                    thread = threading.Thread(
                        target=self._process_path_safe,
                        args=(path,),
                        daemon=True
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join(timeout=0.1)  # Brief timeout to allow checking should_stop
                
                # Sleep briefly to avoid tight looping
                time.sleep(0.1)
                
                # Check if there are any active paths left
                with self.path_lock:
                    active_paths = [p for p in self.paths if p.is_active]
                    if not active_paths:
                        logger.info("All paths completed or inactive, stopping background thread")
                        break
                    
            except Exception as e:
                logger.error(f"Error in background workflow processor: {str(e)}", exc_info=True)
                time.sleep(1)  # Sleep longer on error
    
    def _process_path_safe(self, path):
        """Safely process a path with error handling"""
        try:
            # Set this path's current step as the engine's current step
            # This is for compatibility with the original implementation
            self.current_step = path.current_step
            
            # Process the current step
            result = self._process_step(path.current_step)
            
            # Store the result
            with self.path_lock:
                step_id = path.current_step.get('id', 'unknown') if path.current_step else 'unknown'
                self.results[f"{path.path_id}_{step_id}"] = result
            
            # If we're awaiting input, mark the path as inactive
            if self.session_data.get('awaiting_input', False):
                logger.info(f"Path {path.path_id} is awaiting user input at step {path.current_step.get('id')}")
                path.status = "pending"  # Mark as pending so it can be resumed
                return
            
            # Get the next steps (plural)
            next_steps = self._get_next_steps(path.current_step)
            
            if not next_steps:
                # No next steps, mark this path as completed
                logger.info(f"Path {path.path_id} completed at step {path.current_step.get('id')}")
                with self.path_lock:
                    path.status = "completed"
                    path.is_active = False
                    path.current_step = None
                    self.completed_paths.append(path)
                    self.paths.remove(path)
            else:
                # Create new paths for each next step
                with self.path_lock:
                    # First, deactivate this path
                    path.is_active = False
                    path.status = "completed"
                    self.completed_paths.append(path)
                    self.paths.remove(path)
                    
                    # Then create new paths for each next step
                    for i, next_step in enumerate(next_steps):
                        new_path = WorkflowPath(
                            next_step, 
                            f"{path.path_id}_branch_{i}"
                        )
                        logger.info(f"Created new path {new_path.path_id} from {path.path_id} to step {next_step.get('id')}")
                        self.paths.append(new_path)
        except Exception as e:
            logger.error(f"Error processing path {path.path_id}: {str(e)}", exc_info=True)
            with self.path_lock:
                path.status = "error"
                path.error = str(e)
                path.is_active = False
    
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
        
        return self._process_step(self.current_step)
    
    def _process_step(self, step):
        """
        Process a specific step in the workflow
        
        Args:
            step: The step to process
            
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
                
                # Add this line to debug what's in the session after the function call
                logger.info(f"After function execution, last_reply in session: {self.session_data.get('last_reply', 'NOT FOUND')}")
                
                # Return the result
                return result
            except Exception as e:
                logger.error(f"Error executing function {function_spec}: {str(e)}", exc_info=True)
                self.session_data['error'] = f"Error executing function {function_spec}: {str(e)}"
                return None
        else:
            # If there's no function, return a default result
            return True
    
    def _get_next_steps(self, current_step):
        """
        Get all valid next steps from the current step
        
        Args:
            current_step: The current step node
            
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
                        condition_result = self._process_condition(relationship)
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
    
    def _get_next_step(self):
        """
        LEGACY METHOD: Get the next step in the workflow based on NEXT relationships
        This method maintains compatibility with the original non-parallel implementation.
        It uses _get_next_steps and takes the first valid next step.
        """
        next_steps = self._get_next_steps(self.current_step)
        
        if not next_steps:
            self.current_step = None
            return
            
        # Take the first valid next step for compatibility
        self.current_step = next_steps[0]
    
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
        Process variable references in the input data
        
        Args:
            data: The input data with variables to process
            
        Returns:
            The processed data with variables replaced
        """
        if isinstance(data, dict):
            return {k: self._process_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._process_variables(v) for v in data]
        elif isinstance(data, str):
            # Find variable references like @{node_id}.{key}
            return self._replace_variables(data)
        else:
            return data
    
    def _replace_variables(self, text):
        """
        Replace variable references in text with their values
        
        Args:
            text: The text with variables to replace
            
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
        logger.info(f"Current session data keys: {list(self.session_data.keys())}")
        
        # Now process each match and replace in the text
        for full_match, node_id, key, default_value in matches:
            # Check if the key exists in session data
            if key in self.session_data:
                value = self.session_data[key]
                
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
    
    def continue_workflow(self, user_input=None):
        """
        Continue the workflow after user input
        
        Args:
            user_input: The user's input text
            
        Returns:
            The result of the next action, or None if waiting for more input
        """
        logger.info(f"Continuing workflow with user input: {user_input}")
        
        # Make sure we have a current step to continue from
        if not self.current_step and self.session_data.get('awaiting_input', False):
            logger.warning("No current step but awaiting input, restarting from root")
            try:
                self.current_step = self._get_root_node()
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
                
                # Since we've processed the input, resume all pending paths
                with self.path_lock:
                    for path in self.paths:
                        if path.status == "pending":
                            logger.info(f"Resuming path {path.path_id} after user input")
                            path.status = "pending"  # Ensure it's marked as pending for processing
                    
                # Get the next steps for the current step
                next_steps = self._get_next_steps(self.current_step)
                
                # Log the transitions
                for next_step in next_steps:
                    next_id = next_step.get('id') if next_step else None
                    logger.info(f"Transitioning from {current_id} to {next_id} after user input")
                
                # If we couldn't get any next steps, this is a problem
                if not next_steps:
                    error_msg = f"No next steps found after processing user input from {current_id}"
                    logger.error(error_msg)
                    self.session_data['error'] = error_msg
                    return None
                
                # Set the current step to the first next step for compatibility with existing code
                self.current_step = next_steps[0] if next_steps else None
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

    def get_active_paths_count(self):
        """Get the count of active workflow paths"""
        with self.path_lock:
            return sum(1 for p in self.paths if p.is_active)
    
    def get_path_statuses(self):
        """Get a summary of path statuses"""
        with self.path_lock:
            return {
                'active': sum(1 for p in self.paths if p.is_active),
                'pending': sum(1 for p in self.paths if p.status == "pending"),
                'running': sum(1 for p in self.paths if p.status == "running"),
                'completed': len(self.completed_paths),
                'paths': [str(p) for p in self.paths + self.completed_paths]
            }

# Singleton instance of the workflow engine
_workflow_engine = None

def get_workflow_engine():
    """Get the singleton workflow engine instance"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
