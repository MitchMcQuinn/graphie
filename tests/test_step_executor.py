"""
tests/test_step_executor.py
----------------
This module contains tests for the StepExecutor class.
"""

import pytest
from unittest.mock import Mock, patch
from neo4j import Driver

from core.workflow.state import WorkflowState
from core.workflow.executor import StepExecutor

@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    driver = Mock(spec=Driver)
    session = Mock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver

@pytest.fixture
def mock_state(mock_driver):
    """Create a mock WorkflowState."""
    state = WorkflowState(mock_driver, "test-session")
    state.initialize()
    return state

@pytest.fixture
def executor(mock_driver, mock_state):
    """Create a StepExecutor instance."""
    return StepExecutor(mock_driver, mock_state)

def test_resolve_variables(executor):
    """Test resolving variables in a template."""
    # Add some test outputs to the state
    executor.state.add_step_output("step1", {"value": "test1"})
    executor.state.add_step_output("step2", {"value": "test2"})
    
    # Create a template with variable references
    template = {
        "simple": "@{step1}.value",
        "nested": {
            "value": "@{step2}.value"
        },
        "list": ["@{step1}.value", "@{step2}.value"],
        "static": "static value"
    }
    
    # Resolve variables
    resolved = executor.resolve_variables("current-step", template)
    
    # Check that variables were resolved correctly
    assert resolved["simple"] == "test1"
    assert resolved["nested"]["value"] == "test2"
    assert resolved["list"] == ["test1", "test2"]
    assert resolved["static"] == "static value"

def test_resolve_variable_reference(executor):
    """Test resolving a single variable reference."""
    # Add a test output to the state
    executor.state.add_step_output("test-step", {"value": "test"})
    
    # Resolve a variable reference
    value = executor._resolve_variable_reference("@{test-step}.value")
    
    # Check that the value was resolved correctly
    assert value == "test"

def test_resolve_missing_variable(executor):
    """Test resolving a missing variable reference."""
    # Resolve a non-existent variable reference
    value = executor._resolve_variable_reference("@{missing-step}.value")
    
    # Check that the original reference is returned
    assert value == "@{missing-step}.value"

def test_execute_step(executor):
    """Test executing a step."""
    # Create a mock function module
    mock_module = Mock()
    mock_module.test_function = Mock(return_value={"result": "success"})
    
    # Create a step with a function
    step_data = {
        "function": {
            "module": "test_module",
            "name": "test_function"
        },
        "input": {
            "param": "value"
        }
    }
    
    # Mock the module import
    with patch.dict("sys.modules", {"test_module": mock_module}):
        # Execute the step
        result = executor.execute_step("test-step", step_data)
        
        # Check that the step was executed successfully
        assert result is True
        
        # Check that the function was called with the correct input
        mock_module.test_function.assert_called_once_with(param="value")
        
        # Check that the output was stored
        output = executor.state.get_latest_step_output("test-step")
        assert output == {"result": "success"}

def test_execute_step_error(executor):
    """Test executing a step that raises an error."""
    # Create a mock function that raises an error
    mock_module = Mock()
    mock_module.test_function = Mock(side_effect=Exception("Test error"))
    
    # Create a step with a function
    step_data = {
        "function": {
            "module": "test_module",
            "name": "test_function"
        }
    }
    
    # Mock the module import
    with patch.dict("sys.modules", {"test_module": mock_module}):
        # Execute the step
        result = executor.execute_step("test-step", step_data)
        
        # Check that the step execution failed
        assert result is False
        
        # Check that the step status was updated
        step = executor.state.state["workflow"]["test-step"]
        assert step["status"] == "error"
        assert "Test error" in step["error"]

def test_check_step_dependencies(executor):
    """Test checking step dependencies."""
    # Add some test outputs
    executor.state.add_step_output("dep1", {"value": "test1"})
    executor.state.add_step_output("dep2", {"value": "test2"})
    
    # Check dependencies that exist
    result = executor.check_step_dependencies("test-step", ["dep1", "dep2"])
    assert result is True
    
    # Check dependencies with a missing one
    result = executor.check_step_dependencies("test-step", ["dep1", "missing"])
    assert result is False

def test_execute_step_without_function(executor):
    """Test executing a step without a function."""
    # Create a step without a function
    step_data = {
        "input": {
            "param": "value"
        }
    }
    
    # Execute the step
    result = executor.execute_step("test-step", step_data)
    
    # Check that the step was executed successfully
    assert result is True
    
    # Check that the step status was updated
    step = executor.state.state["workflow"]["test-step"]
    assert step["status"] == "complete" 