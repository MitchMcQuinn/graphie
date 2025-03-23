"""
core/workflow/state.py
----------------
This module implements the WorkflowState class which manages the state of a workflow execution.
It provides methods for state initialization, updates, and persistence in Neo4j.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from neo4j import Driver

logger = logging.getLogger(__name__)

class WorkflowState:
    """
    Manages the state of a workflow execution, including step status, outputs, and messages.
    """
    
    def __init__(self, driver: Driver, session_id: str):
        """
        Initialize a new workflow state.
        
        Args:
            driver: Neo4j driver instance
            session_id: Unique identifier for the workflow session
        """
        self.driver = driver
        self.session_id = session_id
        self.state = {
            "id": session_id,
            "workflow": {
                "root": {
                    "status": "active",
                    "error": ""
                }
            },
            "data": {
                "outputs": {},
                "messages": []
            }
        }
    
    def initialize(self) -> bool:
        """
        Initialize the workflow state in Neo4j.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            with self.driver.session() as session:
                # Create SESSION node with initial state
                session.run("""
                    CREATE (s:SESSION {
                        id: $session_id,
                        state: $state,
                        created_at: datetime(),
                        updated_at: datetime()
                    })
                """, session_id=self.session_id, state=json.dumps(self.state))
                
                logger.info(f"Initialized workflow state for session {self.session_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize workflow state: {str(e)}")
            return False
    
    def load(self) -> bool:
        """
        Load the workflow state from Neo4j.
        
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.state as state
                """, session_id=self.session_id)
                
                record = result.single()
                if not record:
                    logger.error(f"No state found for session {self.session_id}")
                    return False
                
                self.state = json.loads(record['state'])
                logger.info(f"Loaded workflow state for session {self.session_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to load workflow state: {str(e)}")
            return False
    
    def save(self) -> bool:
        """
        Save the current workflow state to Neo4j.
        
        Returns:
            bool: True if saving was successful, False otherwise
        """
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.state = $state,
                        s.updated_at = datetime()
                """, session_id=self.session_id, state=json.dumps(self.state))
                
                logger.info(f"Saved workflow state for session {self.session_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save workflow state: {str(e)}")
            return False
    
    def update_step_status(self, step_id: str, status: str, error: str = "") -> bool:
        """
        Update the status of a workflow step.
        
        Args:
            step_id: ID of the step to update
            status: New status for the step
            error: Optional error message
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            if step_id not in self.state["workflow"]:
                self.state["workflow"][step_id] = {
                    "status": status,
                    "error": error
                }
            else:
                self.state["workflow"][step_id]["status"] = status
                if error:
                    self.state["workflow"][step_id]["error"] = error
            
            return self.save()
        except Exception as e:
            logger.error(f"Failed to update step status: {str(e)}")
            return False
    
    def add_step_output(self, step_id: str, output: Dict[str, Any]) -> bool:
        """
        Add output data for a workflow step.
        
        Args:
            step_id: ID of the step
            output: Output data to store
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            if step_id not in self.state["data"]["outputs"]:
                self.state["data"]["outputs"][step_id] = []
            
            self.state["data"]["outputs"][step_id].append(output)
            return self.save()
        except Exception as e:
            logger.error(f"Failed to add step output: {str(e)}")
            return False
    
    def add_message(self, role: str, content: str) -> bool:
        """
        Add a message to the workflow's message history.
        
        Args:
            role: Role of the message sender (e.g., 'user', 'assistant')
            content: Content of the message
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            self.state["data"]["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            return self.save()
        except Exception as e:
            logger.error(f"Failed to add message: {str(e)}")
            return False
    
    def get_active_steps(self) -> list:
        """
        Get all steps with 'active' status.
        
        Returns:
            list: List of step IDs with active status
        """
        return [
            step_id for step_id, step_data in self.state["workflow"].items()
            if step_data["status"] == "active"
        ]
    
    def get_pending_steps(self) -> list:
        """
        Get all steps with 'pending' status.
        
        Returns:
            list: List of step IDs with pending status
        """
        return [
            step_id for step_id, step_data in self.state["workflow"].items()
            if step_data["status"] == "pending"
        ]
    
    def get_step_outputs(self, step_id: str) -> list:
        """
        Get all outputs for a specific step.
        
        Args:
            step_id: ID of the step
            
        Returns:
            list: List of step outputs
        """
        return self.state["data"]["outputs"].get(step_id, [])
    
    def get_latest_step_output(self, step_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent output for a specific step.
        
        Args:
            step_id: ID of the step
            
        Returns:
            Optional[Dict[str, Any]]: Latest output or None if no outputs exist
        """
        outputs = self.get_step_outputs(step_id)
        return outputs[-1] if outputs else None
    
    def get_messages(self) -> list:
        """
        Get all messages in the workflow.
        
        Returns:
            list: List of messages
        """
        return self.state["data"]["messages"] 