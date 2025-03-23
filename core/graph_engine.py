"""
graph_engine.py
--------------
This module defines the GraphWorkflowEngine class, which implements the graph-based workflow engine for managing conversational workflows with Neo4j.

Purpose:
    Provides a Neo4j-based workflow engine that stores all session state
    in SESSION nodes within the graph database.
"""

import os
import json
import importlib
import re
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from .database import get_neo4j_driver
from .resolve_variable import resolve_variable, process_variables
from .store_memory import store_memory
from .session_manager import get_session_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphWorkflowEngine:
    """
    A workflow engine that stores session state in Neo4j SESSION nodes.
    """
    
    def __init__(self):
        """Initialize the GraphWorkflowEngine."""
        self.driver = get_neo4j_driver()
        if not self.driver:
            logger.error("Failed to initialize Neo4j driver")
        
        # Initialize session manager
        self.session_manager = get_session_manager(self.driver)
        if not self.session_manager:
            logger.error("Failed to initialize session manager")
    
    def create_session(self) -> str:
        """
        Create a new SESSION node in Neo4j.
        
        Returns:
            str: The session ID of the newly created session
        """
        session_id = str(uuid.uuid4())
        
        if not self.driver:
            logger.error("Cannot create session: Neo4j driver not available")
            return session_id
        
        # Use the session manager to create the session
        if self.session_manager.create_session(session_id):
            logger.info(f"Created new SESSION node with ID: {session_id}")
            
            # Verify the session was created
            if self.session_manager.has_session(session_id):
                logger.info(f"Verified SESSION node with ID: {session_id} exists")
            else:
                logger.error(f"Failed to create SESSION node with ID: {session_id}")
            
            return session_id
        else:
            logger.error(f"Failed to create SESSION node with ID: {session_id}")
            return session_id
    
    def has_session(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: The ID of the session to check
            
        Returns:
            bool: True if the session exists, False otherwise
        """
        if not self.session_manager:
            return False
        
        return self.session_manager.has_session(session_id)
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current status of a session.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            dict: The session status information
        """
        if not self.session_manager:
            return {"error": "Session manager not available"}
        
        return self.session_manager.get_session_status(session_id)
    
    def get_frontend_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current state formatted for the frontend.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            dict: The frontend state information
        """
        if not self.driver:
            return {
                "error": True,
                "awaiting_input": False,
                "reply": "Neo4j driver not available"
            }
        
        status = self.get_session_status(session_id)
        
        if 'error' in status:
            return {
                "error": True,
                "awaiting_input": False,
                "reply": status['error']
            }
        
        # Check if the session is awaiting input
        is_awaiting_input = status['status'] == 'awaiting_input'
        
        # Get the latest reply or request from memory
        memory = status['memory']
        
        # First check if we have any reply data, regardless of status
        reply_data = None
        for step_id, outputs in memory.items():
            if outputs and step_id == 'provide-answer':
                last_output = outputs[-1]
                if 'reply' in last_output:
                    reply_data = last_output
                    break
        
        # If we have reply data and we're going back to awaiting input,
        # we should show the reply instead of a new request statement
        if reply_data and is_awaiting_input:
            # We have a meaningful response to show
            reply = reply_data.get('reply', '')
            
            # Find the variable in the get-question node input
            var_ref = None
            try:
                with self.driver.session() as db_session:
                    result = db_session.run("""
                        MATCH (s:STEP {id: 'get-question'})
                        RETURN s.input as input
                    """)
                    record = result.single()
                    if record and record['input']:
                        try:
                            input_data = json.loads(record['input'])
                            if 'query' in input_data:
                                # Parse the conditional reference (format: @{...}|default)
                                query = input_data['query']
                                if '|' in query:
                                    var_ref, default = query.split('|', 1)
                                    var_ref = var_ref.strip()
                        except (json.JSONDecodeError, KeyError):
                            pass
            except Exception as e:
                logger.error(f"Error getting get-question input: {str(e)}")
            
            # Just use the standard variable resolution for the follow-up question
            statement = None
            if var_ref:
                try:
                    # Use the existing variable resolution system
                    result = resolve_variable(self.driver, session_id, var_ref)
                    if result != var_ref:  # If it was resolved successfully
                        statement = result
                        logger.info(f"Resolved follow-up question: {statement}")
                except Exception as e:
                    logger.error(f"Error resolving follow-up question: {str(e)}")
            
            # If we couldn't get a follow-up question, use a generic one
            if not statement:
                statement = "Is there anything else you'd like to know?"
                logger.info(f"Using default follow-up question")
            
            return {
                "awaiting_input": True,
                "reply": reply,
                "statement": statement
            }
            
        # Original handling for awaiting input state (for initial greeting)
        if is_awaiting_input:
            # Find the latest request output
            request_data = None
            for step_id, outputs in memory.items():
                if outputs and step_id.startswith('request-'):
                    last_output = outputs[-1]
                    if 'statement' in last_output:
                        request_data = last_output
            
            statement = request_data.get('statement', 'What would you like to know?') if request_data else 'What would you like to know?'
            
            return {
                "awaiting_input": True,
                "statement": statement
            }
        else:
            # Find the latest reply output
            reply_data = None
            for step_id, outputs in memory.items():
                if outputs and step_id.startswith('reply-'):
                    last_output = outputs[-1]
                    if 'reply' in last_output:
                        reply_data = last_output
            
            # Find the latest generation data for structured output
            generation_data = None
            for step_id, outputs in memory.items():
                if outputs and step_id.startswith('generate-'):
                    last_output = outputs[-1]
                    generation_data = last_output
            
            reply = reply_data.get('reply', '') if reply_data else ''
            
            return {
                "awaiting_input": False,
                "reply": reply,
                "has_pending_steps": len(status['next_steps']) > 0,
                "structured_data": generation_data if generation_data else {}
            }
    def get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get the chat history for a session.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            list: The chat history
        """
        if not self.session_manager:
            return []
        
        return self.session_manager.get_chat_history(session_id)
    
    def start_workflow(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Start a new workflow from the root node.
        
        Args:
            session_id: Optional session ID to use, will create a new one if not provided
            
        Returns:
            dict: The result of starting the workflow, or None if error
        """
        # Create a new session if not provided
        if not session_id:
            session_id = self.create_session()
            logger.info(f"Created new session with ID: {session_id}")
        elif not self.has_session(session_id):
            # Create a new session with the provided ID
            logger.info(f"Session {session_id} does not exist, creating it")
            try:
                with self.driver.session() as db_session:
                    # Create the SESSION node with complex objects as JSON strings
                    db_session.run("""
                        CREATE (s:SESSION {
                            id: $session_id,
                            memory: $memory,
                            next_steps: $next_steps,
                            created_at: datetime(),
                            status: 'active',
                            errors: $errors,
                            chat_history: $chat_history
                        })
                    """, 
                    session_id=session_id,
                    memory='{}',  # Empty JSON object
                    errors='[]',  # Empty JSON array
                    chat_history='[]',  # Empty JSON array
                    next_steps=['root']  # Initial next steps
                    )
                    
                    logger.info(f"Created SESSION node with ID: {session_id}")
            except Exception as e:
                logger.error(f"Error creating session with ID {session_id}: {str(e)}")
                # Fall back to creating a new session with a generated ID
                session_id = self.create_session()
                logger.info(f"Created fallback session with ID: {session_id}")
        
        logger.info(f"Starting workflow for session {session_id}")
        
        # Set next_steps to ['root'] to begin the workflow
        try:
            with self.driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.next_steps = ['root'],
                        s.status = 'active'
                """, session_id=session_id)
            
            # Process the workflow steps
            return self.process_workflow_steps(session_id)
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            
            # Record the error
            self._record_error(session_id, "start_workflow", str(e))
            return None
    
    def _record_error(self, session_id: str, step_id: str, error_message: str) -> None:
        """
        Record an error in the session's errors array.
        
        Args:
            session_id: The session ID
            step_id: The step ID where the error occurred
            error_message: The error message
        """
        try:
            with self.driver.session() as db_session:
                # First get current errors
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.errors as errors
                """, session_id=session_id)
                
                record = result.single()
                if record:
                    # Parse current errors JSON
                    try:
                        errors_str = record['errors'] if record['errors'] else "[]"
                        errors = json.loads(errors_str)
                    except (json.JSONDecodeError, TypeError):
                        errors = []
                    
                    # Add new error
                    errors.append({
                        "step_id": step_id,
                        "error": error_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Update errors as JSON string
                    db_session.run("""
                        MATCH (s:SESSION {id: $session_id})
                        SET s.errors = $errors
                    """, session_id=session_id, errors=json.dumps(errors))
                    
                    logger.info(f"Recorded error for session {session_id}: {error_message}")
        except Exception as e:
            logger.error(f"Error recording error: {str(e)}")
    
    def process_workflow_steps(self, session_id: str) -> Dict[str, Any]:
        """
        Process the next steps in the workflow.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            dict: The result of processing the steps
        """
        if not self.driver:
            return {"error": "Neo4j driver not available"}
        
        status = self.get_session_status(session_id)
        
        if 'error' in status:
            return {"error": status['error']}
        
        # If the session is awaiting input, we can't proceed until input is received
        if status['status'] == 'awaiting_input':
            logger.info(f"Session {session_id} is awaiting input, cannot process steps")
            return {"awaiting_input": True}
        
        # Get the next steps to process
        next_steps = status['next_steps']
        
        if not next_steps:
            logger.info(f"No next steps to process for session {session_id}")
            return {"status": "completed"}
        
        logger.info(f"Processing next steps for session {session_id}: {next_steps}")
        
        # Process each next step
        try:
            processed_steps = []
            has_request_step = False
            
            for step_id in next_steps:
                # Check if this step requires the request utility (which would pause the workflow)
                step_info = self._get_step_info(step_id)
                
                if not step_info:
                    logger.error(f"Step {step_id} not found")
                    continue
                
                # Check if this step uses the request utility (pause the workflow)
                if 'function' in step_info and 'request' in step_info['function']:
                    logger.info(f"Step {step_id} uses request utility, pausing workflow")
                    
                    # Process this step but don't remove it from next_steps yet
                    self._process_step(session_id, step_info)
                    processed_steps.append(step_id)
                    has_request_step = True
                    
                    # Update session status to awaiting input
                    with self.driver.session() as db_session:
                        db_session.run("""
                            MATCH (s:SESSION {id: $session_id})
                            SET s.status = 'awaiting_input'
                        """, session_id=session_id)
                    
                    # Return immediately since we're now waiting for input
                    return {"awaiting_input": True}
                else:
                    # Process the step
                    logger.info(f"Processing non-request step: {step_id}")
                    self._process_step(session_id, step_info)
                    processed_steps.append(step_id)
            
            # Check if any steps were processed
            if not processed_steps:
                logger.warning(f"No steps were processed for session {session_id}")
                return {"status": "no_steps_processed"}
            
            # All steps processed, calculate new next steps
            logger.info(f"Processed steps: {processed_steps}")
            self._update_next_steps(session_id, processed_steps)
            
            # Check if there are more steps to process
            updated_status = self.get_session_status(session_id)
            logger.info(f"Updated next steps: {updated_status['next_steps']}")
            has_more_steps = updated_status['next_steps'] and len(updated_status['next_steps']) > 0
            
            # Continue processing if there are more steps and no request step was encountered
            if has_more_steps and not has_request_step:
                logger.info(f"Continuing to process more steps for session {session_id}")
                return self.process_workflow_steps(session_id)
            
            return {
                "status": "active" if has_more_steps else "completed",
                "has_more_steps": has_more_steps
            }
            
        except Exception as e:
            logger.error(f"Error processing workflow steps: {str(e)}")
            
            # Record the error
            self._record_error(session_id, "process_workflow_steps", str(e))
            
            return {"error": str(e)}
    
    def _get_step_info(self, step_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a step from the graph.
        
        Args:
            step_id: The ID of the step
            
        Returns:
            dict: The step information, or None if not found
        """
        try:
            with self.driver.session() as db_session:
                # First check if the step exists
                check_result = db_session.run("""
                    MATCH (s:STEP {id: $step_id})
                    RETURN count(s) as count
                """, step_id=step_id)
                
                check_record = check_result.single()
                if not check_record or check_record['count'] == 0:
                    logger.error(f"Step with ID '{step_id}' does not exist in the database")
                    return None
                
                # Now get the step details
                result = db_session.run("""
                    MATCH (s:STEP {id: $step_id})
                    RETURN s
                """, step_id=step_id)
                
                record = result.single()
                if not record:
                    logger.error(f"Failed to retrieve step data for ID '{step_id}'")
                    return None
                
                step_info = dict(record['s'])
                logger.info(f"Retrieved step info for '{step_id}': {step_info.get('description', 'No description')}")
                return step_info
        except Exception as e:
            logger.error(f"Error getting step info for '{step_id}': {str(e)}")
            return None
    
    def _process_step(self, session_id: str, step_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single step in the workflow.
        
        Args:
            session_id: The ID of the session
            step_info: Information about the step to process
            
        Returns:
            dict: The result of processing the step, or None if error
        """
        step_id = step_info.get('id', 'unknown')
        logger.info(f"Processing step {step_id} for session {session_id}")
        
        # Check if the step has a function to execute
        if not step_info.get('function'):
            logger.info(f"Step {step_id} has no function, skipping")
            return None
        
        # Parse the function name (assuming module.function format)
        function_spec = step_info['function']
        
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
        
        # Parse input JSON and process variables
        input_data = {}
        if 'input' in step_info and step_info['input']:
            try:
                input_data = json.loads(step_info['input'])
                
                # Process variable references in the input
                input_data = process_variables(self.driver, session_id, input_data)
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing input JSON for step {step_id}: {str(e)}"
                logger.error(error_msg)
                self._record_error(session_id, step_id, error_msg)
                return None
        
        # Import the module and get the function
        try:
            logger.info(f"Importing module {module_name} and function {function_name} for step {step_id}")
            module = importlib.import_module(module_name)
            function = getattr(module, function_name)
            
            # Execute the function - NOTE: We need to adapt utilities to accept the driver and session_id
            # Currently, they expect a session dictionary
            session_data = self._get_memory_as_session_dict(session_id)
            result = function(session_data, input_data)
            
            # Store the function result in the session memory
            if result is not None:
                store_memory(self.driver, session_id, step_id, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error executing function {function_spec} for step {step_id}: {str(e)}"
            logger.error(error_msg)
            self._record_error(session_id, step_id, error_msg)
            return None
    
    def _get_memory_as_session_dict(self, session_id: str) -> Dict[str, Any]:
        """
        Convert the session memory into a session dictionary compatible with existing utilities.
        This is a temporary function to support the transition to the new architecture.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            dict: A session dictionary with memory from the SESSION node
        """
        session_dict = {'id': session_id}
        
        try:
            with self.driver.session() as db_session:
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.memory as memory, s.chat_history as chat_history, s.status as status
                """, session_id=session_id)
                
                record = result.single()
                if not record:
                    return session_dict
                
                # Parse JSON strings
                try:
                    chat_history = json.loads(record['chat_history']) if record['chat_history'] else []
                except (json.JSONDecodeError, TypeError):
                    chat_history = []
                    
                try:
                    memory_str = record['memory'] if record['memory'] else "{}"
                    memory = json.loads(memory_str)
                except (json.JSONDecodeError, TypeError):
                    memory = {}
                
                # Add chat history
                session_dict['chat_history'] = chat_history
                
                # Add awaiting_input flag
                session_dict['awaiting_input'] = record['status'] == 'awaiting_input'
                
                # Add memory as individual keys to match old structure
                for step_id, outputs in memory.items():
                    if outputs:
                        latest_output = outputs[-1]
                        session_dict[step_id] = latest_output
                        
                        # Special keys for backwards compatibility
                        if step_id.startswith('generate-') and isinstance(latest_output, dict):
                            session_dict['generation'] = latest_output
                            # Also add individual keys with generation_ prefix
                            for key, value in latest_output.items():
                                session_dict[f'generation_{key}'] = value
                                
                        if step_id.startswith('reply-') and 'reply' in latest_output:
                            session_dict['last_reply'] = latest_output['reply']
                            
                        if step_id.startswith('request-') and 'statement' in latest_output:
                            session_dict['request_statement'] = latest_output['statement']
                
                return session_dict
                
        except Exception as e:
            logger.error(f"Error getting memory as session dict: {str(e)}")
            return session_dict
    
    def _update_next_steps(self, session_id: str, processed_steps: List[str]) -> None:
        """
        Update the next_steps array in the SESSION node after processing steps.
        
        Args:
            session_id: The ID of the session
            processed_steps: List of step IDs that were processed
        """
        try:
            # Find all outgoing relationships from processed steps
            with self.driver.session() as db_session:
                # First, get all potential next steps with their conditions
                result = db_session.run("""
                    MATCH (s:STEP)-[r:NEXT]->(next:STEP)
                    WHERE s.id IN $step_ids
                    RETURN s.id as source_id, next.id as target_id, r
                """, step_ids=processed_steps)
                
                # Collect all potential next steps
                potential_next_steps = []
                records = list(result)
                
                logger.info(f"Found {len(records)} potential paths from processed steps: {processed_steps}")
                
                for record in records:
                    relationship = dict(record['r'])
                    target_id = record['target_id']
                    source_id = record['source_id']
                    
                    logger.info(f"\n{'='*50}")
                    logger.info(f"Evaluating path from {source_id} to {target_id}")
                    logger.info(f"Relationship properties: {relationship}")
                    
                    # Check if the relationship has conditions
                    conditions = relationship.get('conditions')
                    if conditions:
                        logger.info(f"Found conditions for path {source_id} -> {target_id}: {conditions}")
                        
                        # Parse the conditions string into a JSON object if it's a string
                        if isinstance(conditions, str):
                            try:
                                conditions = json.loads(conditions)
                                logger.info(f"Parsed conditions JSON: {conditions}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing conditions JSON: {str(e)}")
                                logger.info(f"Skipping path {source_id} -> {target_id} due to invalid conditions")
                                continue  # Skip this path if we can't parse conditions
                        
                        # Evaluate conditions
                        condition_result = True
                        for expected_value, var_ref in conditions.items():
                            logger.info(f"\nEvaluating condition: expected {expected_value} for {var_ref}")
                            
                            # Resolve the condition variable
                            resolved = resolve_variable(self.driver, session_id, var_ref)
                            logger.info(f"Resolved variable {var_ref} to {resolved} (type: {type(resolved)})")
                            
                            # Convert expected_value to the same type as resolved for comparison
                            if isinstance(resolved, bool):
                                # For boolean values, we want to match exactly what's expected
                                expected = expected_value.lower() == 'true'
                                logger.info(f"Comparing boolean values: {resolved} == {expected}")
                            elif isinstance(resolved, (int, float)):
                                # For numeric values, convert both to float for comparison
                                expected = float(expected_value)
                                logger.info(f"Comparing numeric values: {resolved} == {expected}")
                            else:
                                # For other values, compare as strings
                                expected = str(expected_value)
                                logger.info(f"Comparing string values: {resolved} == {expected}")
                            
                            # Compare resolved value with expected value
                            # The condition is true only if the resolved value matches the expected value
                            if str(resolved) != str(expected):
                                condition_result = False
                                logger.info(f"Condition failed: got {resolved}, expected {expected}")
                                break
                            else:
                                logger.info(f"Condition passed: {resolved} matches {expected}")
                        
                        if condition_result:
                            potential_next_steps.append(target_id)
                            logger.info(f"All conditions passed for path {source_id} -> {target_id}")
                        else:
                            logger.info(f"Conditions failed for path {source_id} -> {target_id}")
                    else:
                        # No conditions, so this is a next step
                        potential_next_steps.append(target_id)
                        logger.info(f"No conditions for path {source_id} -> {target_id}, adding to next steps")
                
                # Remove duplicates
                next_steps = list(set(potential_next_steps))
                
                # Update the SESSION node
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.next_steps = $next_steps
                """, session_id=session_id, next_steps=next_steps)
                
                logger.info(f"\n{'='*50}")
                logger.info(f"Final next steps for session {session_id}: {next_steps}")
                logger.info(f"{'='*50}\n")
                
        except Exception as e:
            logger.error(f"Error updating next steps: {str(e)}")
    
    def _evaluate_condition(self, session_id: str, function_spec: str, input_json: str) -> bool:
        """
        Evaluate a condition function for a NEXT relationship.
        
        Args:
            session_id: The ID of the session
            function_spec: The function specification (module.function)
            input_json: The input JSON for the function
            
        Returns:
            bool: True if the condition passes, False otherwise
        """
        if not function_spec:
            return True
        
        try:
            # Parse the function name
            if '.' in function_spec:
                parts = function_spec.split('.')
                if len(parts) == 2:
                    module_name = f"utils.{parts[0]}"
                    function_name = parts[1]
                else:
                    module_name, function_name = function_spec.rsplit('.', 1)
            else:
                module_name = 'utils'
                function_name = function_spec
            
            # Parse and process the input JSON
            input_data = {}
            if input_json:
                input_data = json.loads(input_json)
                input_data = process_variables(self.driver, session_id, input_data)
            
            # Import and execute the function
            module = importlib.import_module(module_name)
            function = getattr(module, function_name)
            
            # Execute with the session dictionary
            session_data = self._get_memory_as_session_dict(session_id)
            result = function(session_data, input_data)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return False
    
    def continue_workflow(self, user_input: Optional[str], session_id: str) -> Dict[str, Any]:
        """
        Continue the workflow after receiving user input.
        
        Args:
            user_input: The user's input text
            session_id: The ID of the session
            
        Returns:
            dict: The result of continuing the workflow
        """
        if not self.driver:
            return {"error": "Neo4j driver not available"}
        
        if not self.has_session(session_id):
            logger.warning(f"Session {session_id} not found, creating new session")
            session_id = self.create_session()
        
        # Get current session status
        status = self.get_session_status(session_id)
        
        if 'error' in status:
            return {"error": status['error']}
        
        # Add the user message to chat history
        if user_input:
            try:
                with self.driver.session() as db_session:
                    # First get the current chat history
                    result = db_session.run("""
                        MATCH (s:SESSION {id: $session_id})
                        RETURN s.chat_history as chat_history
                    """, session_id=session_id)
                    
                    record = result.single()
                    if record:
                        # Parse current chat history
                        try:
                            chat_history_str = record['chat_history'] if record['chat_history'] else "[]"
                            chat_history = json.loads(chat_history_str)
                        except (json.JSONDecodeError, TypeError):
                            chat_history = []
                        
                        # Add user message
                        chat_history.append({
                            'role': 'user',
                            'content': user_input
                        })
                        
                        # Update chat history as JSON string
                        db_session.run("""
                            MATCH (s:SESSION {id: $session_id})
                            SET s.chat_history = $chat_history
                        """, session_id=session_id, chat_history=json.dumps(chat_history))
                        
                        logger.info(f"Added user message to chat history for session {session_id}")
            except Exception as e:
                logger.error(f"Error adding message to chat history: {str(e)}")
        
        # Handle the user's response if we were awaiting input
        if status['status'] == 'awaiting_input' and user_input is not None:
            logger.info(f"Handling user input for session {session_id}: {user_input}")
            
            # Store the user's input in memory
            try:
                # Get current step being processed (should be get-question)
                current_step = status['next_steps'][0] if status['next_steps'] else None
                
                if current_step:
                    logger.info(f"Current step is: {current_step}")
                    
                    # Store the user's response
                    step_id_response = f"response-{current_step}"
                    store_memory(self.driver, session_id, step_id_response, {'response': user_input})
                    
                    # Also store under the direct step ID for variable compatibility
                    store_memory(self.driver, session_id, current_step, {'response': user_input})
                    
                    # Check the workflow graph to find the next step after this one
                    with self.driver.session() as db_session:
                        next_result = db_session.run("""
                            MATCH (current:STEP {id: $step_id})-[:NEXT]->(next:STEP)
                            RETURN next.id as next_step_id
                        """, step_id=current_step)
                        
                        next_step_record = next_result.single()
                        next_step = next_step_record['next_step_id'] if next_step_record else None
                        
                        if next_step:
                            logger.info(f"Found next step in workflow: {next_step}")
                            
                            # Update next_steps to the next step in the workflow
                            db_session.run("""
                                MATCH (s:SESSION {id: $session_id})
                                SET s.next_steps = [$next_step],
                                    s.status = 'active'
                            """, session_id=session_id, next_step=next_step)
                            
                            logger.info(f"Updated session {session_id} next_steps to [{next_step}] and status to active")
            
                # Also use the legacy handle_user_response for backward compatibility
                session_data = self._get_memory_as_session_dict(session_id)
                session_data['response'] = user_input
                
                try:
                    from utils.request import handle_user_response
                    handle_user_response(session_data, user_input)
                except Exception as e:
                    logger.error(f"Error in legacy handle_user_response: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error handling user response: {str(e)}")
                self._record_error(session_id, "handle_user_response", str(e))
                return {"error": str(e)}
        
        # Process the next steps in the workflow
        result = self.process_workflow_steps(session_id)
        
        # If we're not awaiting input and have more steps, process them repeatedly
        # until we're either awaiting input or have no more steps
        status = self.get_session_status(session_id)
        attempts = 0
        
        while (status['status'] != 'awaiting_input' and 
               status['next_steps'] and 
               len(status['next_steps']) > 0 and
               attempts < 5):  # Max 5 iterations to prevent infinite loops
            
            logger.info(f"Continuing workflow execution, attempt {attempts+1}")
            attempts += 1
            
            # Process more steps
            self.process_workflow_steps(session_id)
            
            # Update status
            status = self.get_session_status(session_id)
        
        return result

# Singleton instance
_graph_workflow_engine = None

def get_graph_workflow_engine():
    """Get the singleton graph workflow engine instance"""
    global _graph_workflow_engine
    if _graph_workflow_engine is None:
        _graph_workflow_engine = GraphWorkflowEngine()
    return _graph_workflow_engine 