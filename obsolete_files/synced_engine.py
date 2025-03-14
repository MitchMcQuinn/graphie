import os
import json
import importlib
import re
import time
import logging
import threading
from collections import deque
from dotenv import load_dotenv
from fixed_engine import FixedWorkflowEngine, PendingPath

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncedWorkflowEngine(FixedWorkflowEngine):
    """
    Enhanced workflow engine with variable synchronization support.
    This engine extends the fixed engine by adding variable readiness checks
    that continue to retry indefinitely as long as the session is active.
    """
    
    def __init__(self, max_parallel_paths=5, retry_delay=0.5):
        """
        Initialize the synced workflow engine
        
        Args:
            max_parallel_paths: Maximum number of parallel paths to process
            retry_delay: Delay in seconds between retries for variable readiness
        """
        super().__init__(max_parallel_paths)
        self.retry_delay = retry_delay
        self.deferred_steps = {}  # Track steps deferred due to missing variables
        self.session_active = True
    
    def _replace_variables(self, text, session_data):
        """
        Replace variable references in text with their values, with enhanced retry logic
        
        Args:
            text: The text with variables to replace
            session_data: The session object to store state
            
        Returns:
            The text with variables replaced, or None if variables aren't ready
        """
        # Find all variable references with pattern @{node_id}.key or @{node_id}.key|default
        pattern = r'@\{([^}]+)\}\.(\w+)(?:\|([^@]*))?'
        
        # First, collect all matches
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
        
        # Check if all required variables are ready
        missing_variables = []
        for full_match, node_id, key, default_value in matches:
            if key not in session_data and default_value is None:
                missing_variables.append(f"@{{{node_id}}}.{key}")
        
        # If any variables are missing, return None to indicate we need to defer
        if missing_variables:
            logger.warning(f"Variables not ready: {missing_variables}. Will retry later.")
            return None
        
        # Now process each match and replace in the text (all variables are available)
        modified_text = text
        for full_match, node_id, key, default_value in matches:
            # Check if the key exists in session data
            if key in session_data:
                value = session_data[key]
                
                # If this is a JSON string, properly escape the value
                if '"' in text and ('"' + full_match in text or full_match + '"' in text):
                    replacement = json.dumps(str(value))[1:-1]  # Remove the outer quotes
                    logger.info(f"JSON escaping and replacing '{full_match}' with value '{replacement}' from session")
                else:
                    replacement = str(value)
                    logger.info(f"Replacing '{full_match}' with value '{replacement}' from session")
            elif default_value is not None:
                # If this is a JSON string, properly escape the default value
                if '"' in text and ('"' + full_match in text or full_match + '"' in text):
                    replacement = json.dumps(default_value)[1:-1]
                    logger.info(f"JSON escaping and using default value '{replacement}' for variable @{{{node_id}}}.{key}")
                else:
                    replacement = default_value
                    logger.info(f"Variable @{{{node_id}}}.{key} not found in session data, using default value '{default_value}'")
            else:
                # This should never happen since we check for missing variables earlier
                logger.error(f"Variable @{{{node_id}}}.{key} not found in session data and no default provided")
                continue
            
            # Replace the entire matched pattern with the replacement value
            modified_text = modified_text.replace(full_match, replacement)
        
        return modified_text
    
    def _process_step(self, step, session_data):
        """
        Process a step in the workflow with variable readiness checks
        
        Args:
            step: The step to process
            session_data: The session object to store state
            
        Returns:
            The result of processing the step, or None if deferred
        """
        step_id = step.get('id', 'unknown')
        
        # Check if this step is a function step
        if 'function' not in step or not step['function']:
            logger.warning(f"Step {step_id} has no function defined")
            return False
        
        # Get the function input data
        input_data = {}
        if 'input' in step and step['input']:
            try:
                if isinstance(step['input'], str):
                    input_data = json.loads(step['input'])
                else:
                    input_data = step['input']
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing input JSON for step {step_id}: {str(e)}")
                return False
        
        # Process variable references in the input
        try:
            processed_input = self._process_variables(input_data, session_data)
            
            # If variable resolution failed due to missing variables
            if processed_input is None:
                step_key = f"{step_id}_{id(step)}"
                logger.info(f"Deferring execution of step {step_id} - required variables not ready")
                
                # Record this step as deferred
                if step_key not in self.deferred_steps:
                    self.deferred_steps[step_key] = {
                        'step': step,
                        'attempts': 0,
                        'last_attempt': time.time()
                    }
                else:
                    self.deferred_steps[step_key]['attempts'] += 1
                    self.deferred_steps[step_key]['last_attempt'] = time.time()
                
                # Schedule a retry after delay (non-blocking)
                threading.Timer(self.retry_delay, self._retry_deferred_step, 
                               args=[step_key, session_data]).start()
                
                # Return None to indicate this step was deferred
                return None
        except Exception as e:
            logger.error(f"Error processing variables for step {step_id}: {str(e)}", exc_info=True)
            return False
        
        # Now continue with the regular step processing from the parent class
        input_data = processed_input
        
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
        
        # Import the module and get the function
        try:
            logger.info(f"Importing module {module_name} and function {function_name}")
            module = importlib.import_module(f"{module_name}")
            function = getattr(module, function_name)
            
            # Execute the function
            result = function(session_data, input_data)
            logger.info(f"Executed function {function_spec} for step {step_id}")
            
            # If the function set a last_reply, log it
            if 'last_reply' in session_data:
                logger.info(f"After function execution, last_reply in session: {session_data['last_reply']}")
            else:
                logger.info(f"After function execution, last_reply in session: NOT FOUND")
            
            return result
        except Exception as e:
            logger.error(f"Error executing function {function_spec} for step {step_id}: {str(e)}", exc_info=True)
            return False
    
    def _retry_deferred_step(self, step_key, session_data):
        """
        Retry a deferred step after a delay
        
        Args:
            step_key: The key for the deferred step
            session_data: The session object to store state
        """
        # Check if we should stop retrying
        if not self.session_active:
            logger.info(f"Session no longer active, stopping retries for step {step_key}")
            if step_key in self.deferred_steps:
                del self.deferred_steps[step_key]
            return
        
        # Check if the step is still deferred
        if step_key not in self.deferred_steps:
            return
        
        deferred_info = self.deferred_steps[step_key]
        step = deferred_info['step']
        attempts = deferred_info['attempts']
        
        logger.info(f"Retrying deferred step {step.get('id', 'unknown')} (attempt {attempts+1})")
        
        # Try to process the step
        result = self._process_step(step, session_data)
        
        # If the step was successful or returned a definite error (not None),
        # remove it from deferred steps
        if result is not None:
            logger.info(f"Deferred step {step.get('id', 'unknown')} successfully processed")
            del self.deferred_steps[step_key]
            
            # Continue processing the workflow from this step
            self.current_step = step
            self._continue_from_step(step, session_data)
        # Otherwise it's still waiting for variables and will be retried later
    
    def _continue_from_step(self, step, session_data):
        """
        Continue processing the workflow from a completed step
        
        Args:
            step: The completed step
            session_data: The session object to store state
        """
        # Get the next steps
        next_steps = self._get_next_steps(step, session_data)
        
        if next_steps:
            # Add new pending paths for each next step
            for i, next_step in enumerate(next_steps):
                new_path = PendingPath(
                    next_step, 
                    f"deferred_retry_branch_{i}_{time.time()}"
                )
                logger.info(f"Created new path {new_path.path_id} from step {step.get('id', 'unknown')} to step {next_step.get('id', 'unknown')}")
                self.pending_paths.append(new_path)
            
            # Process pending paths
            self.process_pending_paths(session_data)
    
    def mark_session_inactive(self):
        """Mark the session as inactive to stop retrying deferred steps"""
        self.session_active = False
        logger.info("Session marked as inactive, will stop retrying deferred steps")
    
    def get_deferred_steps_info(self):
        """Get information about deferred steps"""
        result = []
        for key, info in self.deferred_steps.items():
            step = info['step']
            result.append({
                'id': step.get('id', 'unknown'),
                'attempts': info['attempts'],
                'time_since_last_attempt': time.time() - info['last_attempt']
            })
        return result


def get_synced_workflow_engine(max_parallel_paths=5, retry_delay=0.5):
    """Get a synced workflow engine instance"""
    return SyncedWorkflowEngine(max_parallel_paths, retry_delay) 