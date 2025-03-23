"""
core/workflow/executor.py
----------------
This module implements the StepExecutor class which handles step execution and variable resolution
in the workflow engine.
"""

import logging
from typing import Dict, Any, Optional, List
from neo4j import Driver

from .state import WorkflowState

logger = logging.getLogger(__name__)

class StepExecutor:
    """
    Handles the execution of workflow steps and variable resolution.
    """
    
    def __init__(self, driver: Driver, state: WorkflowState):
        """
        Initialize the StepExecutor.
        
        Args:
            driver: Neo4j driver instance
            state: WorkflowState instance
        """
        self.driver = driver
        self.state = state
    
    def resolve_variables(self, step_id: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all variable references in a template using the current state.
        
        Args:
            step_id: ID of the current step
            template: Template containing variable references
            
        Returns:
            Dict[str, Any]: Resolved template
        """
        resolved = {}
        
        for key, value in template.items():
            if isinstance(value, str) and value.startswith('@{'):
                # Handle variable reference
                resolved[key] = self._resolve_variable_reference(value)
            elif isinstance(value, dict):
                # Recursively resolve nested dictionaries
                resolved[key] = self.resolve_variables(step_id, value)
            elif isinstance(value, list):
                # Handle lists of values
                resolved[key] = [
                    self.resolve_variables(step_id, item) if isinstance(item, dict)
                    else self._resolve_variable_reference(item) if isinstance(item, str) and item.startswith('@{')
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _resolve_variable_reference(self, ref: str) -> Any:
        """
        Resolve a single variable reference.
        
        Args:
            ref: Variable reference in format @{step_id}.key
            
        Returns:
            Any: Resolved value or original reference if not found
        """
        try:
            # Remove @{ and } from reference
            ref = ref[2:-1]
            
            # Split into step_id and key
            step_id, key = ref.split('.', 1)
            
            # Get latest output for the step
            output = self.state.get_latest_step_output(step_id)
            if not output:
                logger.warning(f"No output found for step {step_id}")
                return ref
            
            # Get value from output
            value = output.get(key)
            if value is None:
                logger.warning(f"Key {key} not found in output for step {step_id}")
                return ref
            
            return value
            
        except Exception as e:
            logger.error(f"Error resolving variable reference {ref}: {str(e)}")
            return ref
    
    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> bool:
        """
        Execute a workflow step.
        
        Args:
            step_id: ID of the step to execute
            step_data: Step configuration data
            
        Returns:
            bool: True if execution was successful, False otherwise
        """
        try:
            # Update step status to active
            self.state.update_step_status(step_id, "active")
            
            # Resolve input variables if any
            inputs = {}
            if "input" in step_data:
                inputs = self.resolve_variables(step_id, step_data["input"])
            
            # Execute step function if defined
            output = None
            if "function" in step_data:
                output = self._execute_function(step_data["function"], inputs)
            
            # Store output if any
            if output is not None:
                self.state.add_step_output(step_id, output)
            
            # Update step status to complete
            self.state.update_step_status(step_id, "complete")
            return True
            
        except Exception as e:
            logger.error(f"Error executing step {step_id}: {str(e)}")
            self.state.update_step_status(step_id, "error", str(e))
            return False
    
    def _execute_function(self, function_data: Dict[str, Any], inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a step's function with the given inputs.
        
        Args:
            function_data: Function configuration data
            inputs: Resolved input variables
            
        Returns:
            Optional[Dict[str, Any]]: Function output or None
        """
        try:
            # Import the function module
            module_name = function_data["module"]
            function_name = function_data["name"]
            
            # Import the module
            module = __import__(module_name, fromlist=[function_name])
            
            # Get the function
            func = getattr(module, function_name)
            
            # Execute the function
            return func(**inputs)
            
        except Exception as e:
            logger.error(f"Error executing function {function_data.get('name')}: {str(e)}")
            return None
    
    def check_step_dependencies(self, step_id: str, dependencies: List[str]) -> bool:
        """
        Check if all dependencies for a step are satisfied.
        
        Args:
            step_id: ID of the step to check
            dependencies: List of step IDs that this step depends on
            
        Returns:
            bool: True if all dependencies are satisfied, False otherwise
        """
        for dep_id in dependencies:
            dep_output = self.state.get_latest_step_output(dep_id)
            if not dep_output:
                logger.info(f"Step {step_id} waiting for dependency {dep_id}")
                return False
        
        return True 