"""
tests/test_graphql_resolver.py
----------------
This module contains tests for the WorkflowGraphQLResolver class.
"""

import pytest
from unittest.mock import Mock, patch
from neo4j import Driver

from core.workflow.graphql import WorkflowGraphQLResolver

@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    driver = Mock(spec=Driver)
    session = Mock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver

@pytest.fixture
def resolver(mock_driver):
    """Create a WorkflowGraphQLResolver instance."""
    return WorkflowGraphQLResolver(mock_driver)

def test_resolve_frontend_state_success(resolver):
    """Test resolving frontend state successfully."""
    # Mock workflow engine response
    mock_status = {
        "active_steps": ["step1"],
        "pending_steps": ["step2"],
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    }
    
    with patch.object(resolver.engine, "get_session_status", return_value=mock_status):
        result = resolver.resolve_frontend_state("test-session")
        
        assert result["awaitingInput"] is False
        assert result["reply"] == "Hi there!"
        assert result["hasPendingSteps"] is True
        assert result["error"] is False

def test_resolve_frontend_state_error(resolver):
    """Test resolving frontend state with error."""
    # Mock workflow engine error
    with patch.object(resolver.engine, "get_session_status", side_effect=Exception("Test error")):
        result = resolver.resolve_frontend_state("test-session")
        
        assert result["awaitingInput"] is False
        assert result["error"] is True
        assert result["reply"] == "An error occurred"

def test_resolve_chat_history(resolver):
    """Test resolving chat history."""
    # Mock workflow engine response
    mock_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    with patch.object(resolver.engine, "get_session_status", return_value={"messages": mock_messages}):
        result = resolver.resolve_chat_history("test-session")
        
        assert result == mock_messages

def test_resolve_has_session(resolver):
    """Test checking if session exists."""
    # Test existing session
    with patch.object(resolver.engine, "get_session_status", return_value={"active_steps": []}):
        assert resolver.resolve_has_session("test-session") is True
    
    # Test non-existing session
    with patch.object(resolver.engine, "get_session_status", side_effect=ValueError("Session not found")):
        assert resolver.resolve_has_session("invalid-session") is False

def test_resolve_session_status(resolver):
    """Test resolving session status."""
    # Mock workflow engine response
    mock_status = {
        "active_steps": ["step1"],
        "pending_steps": ["step2"],
        "messages": [{"role": "user", "content": "Hello"}]
    }
    
    with patch.object(resolver.engine, "get_session_status", return_value=mock_status):
        result = resolver.resolve_session_status("test-session")
        
        assert result["status"] == "active"
        assert result["nextSteps"] == ["step1", "step2"]
        assert result["hasError"] is False
        assert result["hasChatHistory"] is True

def test_resolve_start_workflow(resolver):
    """Test starting a new workflow."""
    # Mock workflow engine responses
    with patch.object(resolver.engine, "create_session", return_value="new-session"), \
         patch.object(resolver.engine, "process_session", return_value=True), \
         patch.object(resolver, "resolve_frontend_state", return_value={"awaitingInput": False}):
        
        result = resolver.resolve_start_workflow()
        
        assert result["success"] is True
        assert result["status"] == "active"
        assert result["hasMoreSteps"] is False

def test_resolve_start_workflow_error(resolver):
    """Test starting workflow with error."""
    # Mock workflow engine error
    with patch.object(resolver.engine, "create_session", side_effect=Exception("Test error")):
        result = resolver.resolve_start_workflow()
        
        assert result["success"] is False
        assert result["status"] == "error"
        assert result["errorMessage"] == "Test error"

def test_resolve_send_message(resolver):
    """Test sending a message to the workflow."""
    # Mock workflow engine responses
    with patch.object(resolver.engine, "add_user_input", return_value=True), \
         patch.object(resolver, "resolve_frontend_state", return_value={"awaitingInput": False}):
        
        result = resolver.resolve_send_message("test-session", "Hello")
        
        assert result["success"] is True
        assert result["status"] == "active"
        assert result["hasMoreSteps"] is False

def test_resolve_send_message_error(resolver):
    """Test sending message with error."""
    # Mock workflow engine error
    with patch.object(resolver.engine, "add_user_input", side_effect=Exception("Test error")):
        result = resolver.resolve_send_message("test-session", "Hello")
        
        assert result["success"] is False
        assert result["status"] == "error"
        assert result["errorMessage"] == "Test error"

def test_resolve_continue_processing(resolver):
    """Test continuing workflow processing."""
    # Mock workflow engine responses
    with patch.object(resolver.engine, "process_session", return_value=True), \
         patch.object(resolver, "resolve_frontend_state", return_value={"awaitingInput": False}):
        
        result = resolver.resolve_continue_processing("test-session")
        
        assert result["success"] is True
        assert result["status"] == "active"
        assert result["hasMoreSteps"] is False

def test_resolve_continue_processing_error(resolver):
    """Test continuing processing with error."""
    # Mock workflow engine error
    with patch.object(resolver.engine, "process_session", side_effect=Exception("Test error")):
        result = resolver.resolve_continue_processing("test-session")
        
        assert result["success"] is False
        assert result["status"] == "error"
        assert result["errorMessage"] == "Test error"

def test_frontend_state_awaiting_input(resolver):
    """Test frontend state when awaiting input."""
    # Mock workflow engine response with no active or pending steps
    mock_status = {
        "active_steps": [],
        "pending_steps": [],
        "messages": [
            {"role": "assistant", "content": "What would you like to know?"}
        ]
    }
    
    with patch.object(resolver.engine, "get_session_status", return_value=mock_status):
        result = resolver.resolve_frontend_state("test-session")
        
        assert result["awaitingInput"] is True
        assert result["statement"] == "What would you like to know?"
        assert result["hasPendingSteps"] is False

def test_frontend_state_with_error(resolver):
    """Test frontend state with workflow error."""
    # Mock workflow engine response with error
    mock_status = {
        "error": "Workflow error occurred"
    }
    
    with patch.object(resolver.engine, "get_session_status", return_value=mock_status):
        result = resolver.resolve_frontend_state("test-session")
        
        assert result["awaitingInput"] is False
        assert result["error"] is True
        assert result["reply"] == "Workflow error occurred" 