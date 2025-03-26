"""
core/workflow/graphql.py
----------------
This module provides GraphQL resolvers that use the graph-based workflow engine.
"""

import logging
from typing import Dict, Any, Optional
from neo4j import Driver

from ..graph_engine import get_graph_workflow_engine

logger = logging.getLogger(__name__)

class WorkflowGraphQLResolver:
    """
    GraphQL resolver that uses the graph-based workflow engine.
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize the resolver.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self.engine = get_graph_workflow_engine()
    
    def resolve_frontend_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get frontend state for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict[str, Any]: Frontend state
        """
        try:
            frontend_state = self.engine.get_frontend_state(session_id)
            
            # Check for error
            if frontend_state.get("error"):
                return {
                    "awaitingInput": False,
                    "error": True,
                    "reply": frontend_state.get("reply", "An error occurred")
                }
            
            return {
                "awaitingInput": frontend_state.get("awaiting_input", False),
                "reply": frontend_state.get("reply", ""),
                "statement": frontend_state.get("statement", "What would you like to know?"),
                "hasPendingSteps": frontend_state.get("has_pending_steps", False),
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
            return self.engine.get_chat_history(session_id)
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
            return self.engine.has_session(session_id)
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
                "status": status.get("status", "error"),
                "nextSteps": status.get("next_steps", []),
                "hasError": "error" in status,
                "errorMessage": status.get("error"),
                "hasChatHistory": bool(status.get("chat_history", []))
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
            # Start the workflow
            result = self.engine.start_workflow(session_id)
            
            if not result:
                raise Exception("Failed to start workflow")
            
            # Get frontend state
            frontend_state = self.resolve_frontend_state(session_id or result.get("session_id"))
            
            return {
                "frontendState": frontend_state,
                "success": True,
                "errorMessage": None,
                "hasMoreSteps": frontend_state.get("hasPendingSteps", False),
                "status": "active"
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
            # Continue the workflow with the message
            result = self.engine.continue_workflow(message, session_id)
            
            if "error" in result:
                raise Exception(result["error"])
            
            # Get frontend state
            frontend_state = self.resolve_frontend_state(session_id)
            
            return {
                "frontendState": frontend_state,
                "success": True,
                "errorMessage": None,
                "hasMoreSteps": frontend_state.get("hasPendingSteps", False),
                "status": "active"
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
            # Process the next steps
            result = self.engine.process_workflow_steps(session_id)
            
            if "error" in result:
                raise Exception(result["error"])
            
            # Get frontend state
            frontend_state = self.resolve_frontend_state(session_id)
            
            return {
                "frontendState": frontend_state,
                "success": True,
                "errorMessage": None,
                "hasMoreSteps": frontend_state.get("hasPendingSteps", False),
                "status": "active"
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