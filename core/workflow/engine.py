"""
core/workflow/engine.py
----------------
This module implements the main WorkflowEngine class that coordinates the workflow execution
using the state manager, step executor, and path evaluator.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from neo4j import Driver

from .state import WorkflowState
from .executor import StepExecutor
from .path import PathEvaluator

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Main workflow engine that coordinates workflow execution.
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize the WorkflowEngine.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
    
    def create_session(self) -> Optional[str]:
        """
        Create a new workflow session.
        
        Returns:
            Optional[str]: Session ID if successful, None otherwise
        """
        try:
            session_id = str(uuid.uuid4())
            state = WorkflowState(self.driver, session_id)
            
            if state.initialize():
                logger.info(f"Created new workflow session: {session_id}")
                return session_id
            else:
                logger.error("Failed to initialize workflow state")
                return None
                
        except Exception as e:
            logger.error(f"Error creating workflow session: {str(e)}")
            return None
    
    def process_session(self, session_id: str) -> bool:
        """
        Process a workflow session, executing active steps and evaluating paths.
        
        Args:
            session_id: ID of the session to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Initialize components
            state = WorkflowState(self.driver, session_id)
            if not state.load():
                logger.error(f"Failed to load state for session {session_id}")
                return False
            
            executor = StepExecutor(self.driver, state)
            path_evaluator = PathEvaluator(self.driver, state, executor)
            
            # Process until no active steps remain
            while True:
                # Get active steps
                active_steps = state.get_active_steps()
                if not active_steps:
                    break
                
                # Process each active step
                for step_id in active_steps:
                    # Get step data
                    step_data = self._get_step_data(step_id)
                    if not step_data:
                        logger.error(f"Failed to get data for step {step_id}")
                        continue
                    
                    # Check dependencies
                    dependencies = path_evaluator.get_step_dependencies(step_id)
                    if not executor.check_step_dependencies(step_id, dependencies):
                        state.update_step_status(step_id, "pending")
                        continue
                    
                    # Execute step
                    if executor.execute_step(step_id, step_data):
                        # Evaluate paths and activate next steps
                        next_steps = path_evaluator.evaluate_paths(step_id)
                        path_evaluator.activate_steps(next_steps)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing session {session_id}: {str(e)}")
            return False
    
    def _get_step_data(self, step_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration data for a step.
        
        Args:
            step_id: ID of the step
            
        Returns:
            Optional[Dict[str, Any]]: Step configuration data or None if not found
        """
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:STEP {id: $step_id})
                    RETURN s.input as input, s.function as function
                """, step_id=step_id)
                
                record = result.single()
                if not record:
                    return None
                
                return {
                    "input": record['input'] if record['input'] else {},
                    "function": record['function'] if record['function'] else None
                }
                
        except Exception as e:
            logger.error(f"Error getting step data: {str(e)}")
            return None
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current status of a workflow session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict[str, Any]: Session status information
        """
        try:
            state = WorkflowState(self.driver, session_id)
            if not state.load():
                return {"error": "Failed to load session state"}
            
            return {
                "active_steps": state.get_active_steps(),
                "pending_steps": state.get_pending_steps(),
                "messages": state.get_messages()
            }
            
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return {"error": str(e)}
    
    def add_user_input(self, session_id: str, message: str) -> bool:
        """
        Add user input to a workflow session.
        
        Args:
            session_id: ID of the session
            message: User message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            state = WorkflowState(self.driver, session_id)
            if not state.load():
                return False
            
            if state.add_message("user", message):
                # Process the session to handle the new input
                return self.process_session(session_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding user input: {str(e)}")
            return False 