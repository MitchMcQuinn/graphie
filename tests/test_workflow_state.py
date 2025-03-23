"""
tests/test_workflow_state.py
----------------
This module contains tests for the WorkflowState class.
"""

import pytest
import json
from unittest.mock import Mock, patch
from neo4j import Driver

from core.workflow.state import WorkflowState

@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    driver = Mock(spec=Driver)
    session = Mock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver

@pytest.fixture
def workflow_state(mock_driver):
    """Create a WorkflowState instance with a mock driver."""
    return WorkflowState(mock_driver, "test-session")

def test_initialize(workflow_state, mock_driver):
    """Test initializing a new workflow state."""
    session = mock_driver.session.return_value.__enter__.return_value
    session.run.return_value = None
    
    # Initialize the state
    result = workflow_state.initialize()
    
    # Check that the state was initialized
    assert result is True
    
    # Check that the correct query was run
    session.run.assert_called_once()
    args = session.run.call_args[0]
    
    # Check that the query creates a SESSION node
    assert "CREATE (s:SESSION" in args[0]
    
    # Check that the state was passed correctly
    kwargs = session.run.call_args[1]
    state = json.loads(kwargs["state"])
    assert state["id"] == "test-session"
    assert state["workflow"]["root"]["status"] == "active"
    assert state["workflow"]["root"]["error"] == ""
    assert state["data"]["outputs"] == {}
    assert state["data"]["messages"] == []

def test_load(workflow_state, mock_driver):
    """Test loading workflow state."""
    session = mock_driver.session.return_value.__enter__.return_value
    
    # Mock the query result
    mock_record = Mock()
    mock_record["state"] = json.dumps({
        "id": "test-session",
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
    })
    session.run.return_value.single.return_value = mock_record
    
    # Load the state
    result = workflow_state.load()
    
    # Check that the state was loaded
    assert result is True
    assert workflow_state.state["id"] == "test-session"
    assert workflow_state.state["workflow"]["root"]["status"] == "active"
    
    # Check that the correct query was run
    session.run.assert_called_once()
    args = session.run.call_args[0]
    assert "MATCH (s:SESSION" in args[0]

def test_save(workflow_state, mock_driver):
    """Test saving workflow state."""
    session = mock_driver.session.return_value.__enter__.return_value
    session.run.return_value = None
    
    # Save the state
    result = workflow_state.save()
    
    # Check that the state was saved
    assert result is True
    
    # Check that the correct query was run
    session.run.assert_called_once()
    args = session.run.call_args[0]
    assert "MATCH (s:SESSION" in args[0]
    assert "SET s.state" in args[0]

def test_update_step_status(workflow_state):
    """Test updating step status."""
    # Update step status
    result = workflow_state.update_step_status("test-step", "active")
    
    # Check that the status was updated
    assert result is True
    assert workflow_state.state["workflow"]["test-step"]["status"] == "active"
    assert workflow_state.state["workflow"]["test-step"]["error"] == ""

def test_add_step_output(workflow_state):
    """Test adding step output."""
    output = {"result": "test"}
    
    # Add step output
    result = workflow_state.add_step_output("test-step", output)
    
    # Check that the output was added
    assert result is True
    assert workflow_state.state["data"]["outputs"]["test-step"] == [output]

def test_add_message(workflow_state):
    """Test adding a message."""
    # Add a message
    result = workflow_state.add_message("user", "test message")
    
    # Check that the message was added
    assert result is True
    messages = workflow_state.state["data"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "test message"

def test_get_active_steps(workflow_state):
    """Test getting active steps."""
    # Add some steps with different statuses
    workflow_state.update_step_status("step1", "active")
    workflow_state.update_step_status("step2", "pending")
    workflow_state.update_step_status("step3", "active")
    
    # Get active steps
    active_steps = workflow_state.get_active_steps()
    
    # Check that only active steps are returned
    assert len(active_steps) == 2
    assert "step1" in active_steps
    assert "step3" in active_steps

def test_get_pending_steps(workflow_state):
    """Test getting pending steps."""
    # Add some steps with different statuses
    workflow_state.update_step_status("step1", "active")
    workflow_state.update_step_status("step2", "pending")
    workflow_state.update_step_status("step3", "pending")
    
    # Get pending steps
    pending_steps = workflow_state.get_pending_steps()
    
    # Check that only pending steps are returned
    assert len(pending_steps) == 2
    assert "step2" in pending_steps
    assert "step3" in pending_steps

def test_get_step_outputs(workflow_state):
    """Test getting step outputs."""
    # Add some outputs
    output1 = {"result": "test1"}
    output2 = {"result": "test2"}
    workflow_state.add_step_output("test-step", output1)
    workflow_state.add_step_output("test-step", output2)
    
    # Get outputs
    outputs = workflow_state.get_step_outputs("test-step")
    
    # Check that all outputs are returned in order
    assert len(outputs) == 2
    assert outputs[0] == output1
    assert outputs[1] == output2

def test_get_latest_step_output(workflow_state):
    """Test getting latest step output."""
    # Add some outputs
    output1 = {"result": "test1"}
    output2 = {"result": "test2"}
    workflow_state.add_step_output("test-step", output1)
    workflow_state.add_step_output("test-step", output2)
    
    # Get latest output
    output = workflow_state.get_latest_step_output("test-step")
    
    # Check that the latest output is returned
    assert output == output2

def test_get_messages(workflow_state):
    """Test getting messages."""
    # Add some messages
    workflow_state.add_message("user", "test message 1")
    workflow_state.add_message("assistant", "test message 2")
    
    # Get messages
    messages = workflow_state.get_messages()
    
    # Check that all messages are returned in order
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "test message 1"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "test message 2" 