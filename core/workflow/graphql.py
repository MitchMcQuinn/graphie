"""
core/workflow/graphql.py
----------------
This module provides GraphQL resolvers that use the new workflow engine.
"""

import logging
from typing import Dict, Any, Optional
from neo4j import Driver

from .engine import WorkflowEngine

logger = logging.getLogger(__name__)

class WorkflowGraphQLResolver:
    """
    GraphQL resolver that uses the new workflow engine.
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize the resolver.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self.engine = WorkflowEngine(driver)
    
    def resolve_frontend_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get frontend state for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict[str, Any]: Frontend state
        """
        try:
            status = self.engine.get_session_status(session_id)
            
            # Check for error
            if "error" in status:
                return {
                    "awaitingInput": False,
                    "error": True,
                    "reply": status["error"]
                }
            
            # Get active and pending steps
            active_steps = status.get("active_steps", [])
            pending_steps = status.get("pending_steps", [])
            messages = status.get("messages", [])
            
            # Get the latest message
            latest_message = messages[-1] if messages else None
            
            # Determine if we're awaiting input
            awaiting_input = not active_steps and not pending_steps
            
            # Get the reply from the latest assistant message
            reply = None
            for msg in reversed(messages):
                if msg["role"] == "assistant":
                    reply = msg["content"]
                    break
            
            # Get the statement from the latest user message
            statement = None
            if awaiting_input:
                for msg in reversed(messages):
                    if msg["role"] == "assistant" and "statement" in msg:
                        statement = msg["statement"]
                        break
                if not statement:
                    statement = "What would you like to know?"
            
            return {
                "awaitingInput": awaiting_input,
                "reply": reply,
                "statement": statement,
                "hasPendingSteps": bool(pending_steps),
                "structuredData": None,
                "error": False
            }
            
        except Exception as e:
            logger.error(f"Error getting frontend state: {str(e)}")
            return {
                "awaitingInput": False,
                "error": True,
                "reply": "An error occurred"
            }
    
    def resolve_chat_history(self, session_id: str) -> list:
        """
        Get chat history for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            list: Chat history
        """
        try:
            status = self.engine.get_session_status(session_id)
            return status.get("messages", [])
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return []
    
    def resolve_has_session(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: ID of the session
            
        Returns:
            bool: True if session exists, False otherwise
        """
        try:
            status = self.engine.get_session_status(session_id)
            return "error" not in status
        except Exception as e:
            logger.error(f"Error checking session: {str(e)}")
            return False
    
    def resolve_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get session status.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict[str, Any]: Session status
        """
        try:
            status = self.engine.get_session_status(session_id)
            
            return {
                "status": "active" if status.get("active_steps") else "pending" if status.get("pending_steps") else "awaiting_input",
                "nextSteps": status.get("active_steps", []) + status.get("pending_steps", []),
                "hasError": "error" in status,
                "errorMessage": status.get("error"),
                "hasChatHistory": bool(status.get("messages", []))
            }
            
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return {
                "status": "error",
                "nextSteps": [],
                "hasError": True,
                "errorMessage": str(e),
                "hasChatHistory": False
            }
    
    def resolve_start_workflow(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new workflow.
        
        Args:
            session_id: Optional session ID
            
        Returns:
            Dict[str, Any]: Workflow result
        """
        try:
            # Create new session if not provided
            if not session_id:
                session_id = self.engine.create_session()
                if not session_id:
                    raise Exception("Failed to create session")
            
            # Process the session
            success = self.engine.process_session(session_id)
            
            # Get frontend state
            frontend_state = self.resolve_frontend_state(session_id)
            
            return {
                "frontendState": frontend_state,
                "success": success,
                "errorMessage": None if success else "Failed to process session",
                "hasMoreSteps": frontend_state.get("hasPendingSteps", False),
                "status": "active" if success else "error"
            }
            
        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            return {
                "frontendState": {
                    "awaitingInput": False,
                    "error": True,
                    "reply": "Failed to start workflow"
                },
                "success": False,
                "errorMessage": str(e),
                "hasMoreSteps": False,
                "status": "error"
            }
    
    def resolve_send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message to the workflow.
        
        Args:
            session_id: ID of the session
            message: User message
            
        Returns:
            Dict[str, Any]: Workflow result
        """
        try:
            # Add user input
            success = self.engine.add_user_input(session_id, message)
            
            # Get frontend state
            frontend_state = self.resolve_frontend_state(session_id)
            
            return {
                "frontendState": frontend_state,
                "success": success,
                "errorMessage": None if success else "Failed to process message",
                "hasMoreSteps": frontend_state.get("hasPendingSteps", False),
                "status": "active" if success else "error"
            }
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {
                "frontendState": {
                    "awaitingInput": False,
                    "error": True,
                    "reply": "Failed to process message"
                },
                "success": False,
                "errorMessage": str(e),
                "hasMoreSteps": False,
                "status": "error"
            }
    
    def resolve_continue_processing(self, session_id: str) -> Dict[str, Any]:
        """
        Continue processing workflow steps.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict[str, Any]: Workflow result
        """
        try:
            # Process the session
            success = self.engine.process_session(session_id)
            
            # Get frontend state
            frontend_state = self.resolve_frontend_state(session_id)
            
            return {
                "frontendState": frontend_state,
                "success": success,
                "errorMessage": None if success else "Failed to process session",
                "hasMoreSteps": frontend_state.get("hasPendingSteps", False),
                "status": "active" if success else "error"
            }
            
        except Exception as e:
            logger.error(f"Error continuing processing: {str(e)}")
            return {
                "frontendState": {
                    "awaitingInput": False,
                    "error": True,
                    "reply": "Failed to continue processing"
                },
                "success": False,
                "errorMessage": str(e),
                "hasMoreSteps": False,
                "status": "error"
            } 