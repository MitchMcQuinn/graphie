"""
tests/test_workflow_engine.py
----------------
This module contains tests for the WorkflowEngine class.
"""

import pytest
from unittest.mock import Mock, patch
from neo4j import Driver

from core.workflow.state import WorkflowState
from core.workflow.executor import StepExecutor
from core.workflow.evaluator import PathEvaluator
from core.workflow.engine import WorkflowEngine

@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    driver = Mock(spec=Driver)
    session = Mock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver

@pytest.fixture
def mock_workflow_state(mock_driver):
    """Create a mock WorkflowState."""
    state = WorkflowState(mock_driver, "test-session")
    state.initialize()
    return state

@pytest.fixture
def mock_step_executor(mock_driver, mock_workflow_state):
    """Create a mock StepExecutor."""
    executor = StepExecutor(mock_driver, mock_workflow_state)
    return executor

@pytest.fixture
def mock_path_evaluator(mock_driver, mock_workflow_state):
    """Create a mock PathEvaluator."""
    evaluator = PathEvaluator(mock_driver, mock_workflow_state)
    return evaluator

@pytest.fixture
def workflow_engine(mock_driver):
    """Create a WorkflowEngine instance."""
    return WorkflowEngine(mock_driver)

def test_create_session(workflow_engine):
    """Test creating a new workflow session."""
    session_id = workflow_engine.create_session()
    assert isinstance(session_id, str)
    assert len(session_id) > 0

def test_get_session_state(workflow_engine):
    """Test getting session state."""
    # Create a session
    session_id = workflow_engine.create_session()
    
    # Get session state
    state = workflow_engine.get_session_state(session_id)
    assert isinstance(state, dict)
    assert "workflow" in state

def test_process_step(workflow_engine, mock_workflow_state, mock_step_executor):
    """Test processing a single step."""
    session_id = workflow_engine.create_session()
    
    # Mock step data
    step_data = {
        "id": "test-step",
        "function": {
            "module": "test_module",
            "name": "test_function"
        },
        "input": {
            "param": "value"
        }
    }
    
    # Mock successful step execution
    with patch.object(StepExecutor, "execute_step", return_value=True):
        result = workflow_engine.process_step(session_id, step_data)
        assert result is True

def test_evaluate_paths(workflow_engine, mock_workflow_state, mock_path_evaluator):
    """Test evaluating workflow paths."""
    session_id = workflow_engine.create_session()
    
    # Mock path data
    paths = [
        {
            "conditions": ["@{step1}.value > 40"],
            "next_step": "step2"
        },
        {
            "conditions": ["@{step1}.value <= 40"],
            "next_step": "step3"
        }
    ]
    
    # Add test data to state
    workflow_engine.get_session_state(session_id)["step1"] = {"value": 42}
    
    # Mock path evaluation
    with patch.object(PathEvaluator, "evaluate_path_conditions", side_effect=[True, False]):
        next_step = workflow_engine.evaluate_paths(session_id, paths)
        assert next_step == "step2"

def test_process_workflow(workflow_engine):
    """Test processing a complete workflow."""
    session_id = workflow_engine.create_session()
    
    # Mock workflow definition
    workflow = {
        "steps": {
            "step1": {
                "function": {
                    "module": "test_module",
                    "name": "test_function1"
                },
                "input": {"param1": "value1"}
            },
            "step2": {
                "function": {
                    "module": "test_module",
                    "name": "test_function2"
                },
                "input": {"param2": "value2"}
            }
        },
        "paths": [
            {
                "from": "step1",
                "conditions": ["@{step1}.status == 'complete'"],
                "to": "step2"
            }
        ]
    }
    
    # Mock step execution and path evaluation
    with patch.object(StepExecutor, "execute_step", return_value=True), \
         patch.object(PathEvaluator, "evaluate_path_conditions", return_value=True):
        
        # Process workflow
        result = workflow_engine.process_workflow(session_id, workflow)
        assert result is True

def test_handle_error(workflow_engine):
    """Test error handling during workflow processing."""
    session_id = workflow_engine.create_session()
    
    # Mock step that raises an error
    step_data = {
        "id": "error-step",
        "function": {
            "module": "test_module",
            "name": "error_function"
        }
    }
    
    # Mock step execution that raises an error
    with patch.object(StepExecutor, "execute_step", side_effect=Exception("Test error")):
        result = workflow_engine.process_step(session_id, step_data)
        assert result is False
        
        # Check error state
        state = workflow_engine.get_session_state(session_id)
        assert state["workflow"]["error-step"]["status"] == "error"
        assert "Test error" in state["workflow"]["error-step"]["error"]

def test_parallel_step_processing(workflow_engine):
    """Test processing parallel steps."""
    session_id = workflow_engine.create_session()
    
    # Mock parallel steps
    parallel_steps = [
        {
            "id": "step1",
            "function": {"module": "test_module", "name": "function1"}
        },
        {
            "id": "step2",
            "function": {"module": "test_module", "name": "function2"}
        }
    ]
    
    # Mock successful execution for all steps
    with patch.object(StepExecutor, "execute_step", return_value=True):
        results = workflow_engine.process_parallel_steps(session_id, parallel_steps)
        assert all(results)
        assert len(results) == 2

def test_workflow_state_persistence(workflow_engine, mock_driver):
    """Test workflow state persistence."""
    session_id = workflow_engine.create_session()
    
    # Add some state data
    state = workflow_engine.get_session_state(session_id)
    state["test_key"] = "test_value"
    
    # Save state
    workflow_engine.save_session_state(session_id, state)
    
    # Retrieve state
    loaded_state = workflow_engine.get_session_state(session_id)
    assert loaded_state["test_key"] == "test_value"

def test_invalid_session(workflow_engine):
    """Test handling invalid session IDs."""
    with pytest.raises(ValueError):
        workflow_engine.get_session_state("invalid-session-id")

def test_workflow_validation(workflow_engine):
    """Test workflow definition validation."""
    # Invalid workflow missing required fields
    invalid_workflow = {
        "steps": {}  # Missing paths
    }
    
    with pytest.raises(ValueError):
        workflow_engine.validate_workflow(invalid_workflow)
    
    # Valid workflow
    valid_workflow = {
        "steps": {
            "step1": {
                "function": {
                    "module": "test_module",
                    "name": "test_function"
                }
            }
        },
        "paths": []
    }
    
    assert workflow_engine.validate_workflow(valid_workflow) is True 