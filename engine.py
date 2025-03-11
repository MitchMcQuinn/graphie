import os
import json
import importlib
import re
import logging
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
        
        # Get the root node
        try:
            self.current_step = self._get_root_node()
            logger.info(f"Starting workflow with root node: {self.current_step.get('id')}")
            
            # Process the root node
            return self.process_current_step()
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
            self.session_data['error'] = f"Error starting workflow: {str(e)}"
            return None
    
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
                
                # Add this line to debug what's in the session after the function call
                logger.info(f"After function execution, last_reply in session: {self.session_data.get('last_reply', 'NOT FOUND')}")
                
                # If we're awaiting input, return None to indicate we should pause
                if self.session_data.get('awaiting_input', False):
                    logger.info(f"Step {current_step_id} is awaiting user input")
                    return None
                
                # Get the next step
                previous_step = self.current_step
                self._get_next_step()
                
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
                    self.current_step = None
                    return
                
                # Get the first valid next step
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
                replacement = str(value)
                logger.info(f"Replacing '{full_match}' with value '{replacement}' from session")
            elif default_value is not None:
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
                
                # Since we've processed the input, get the next step
                self._get_next_step()
                
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
