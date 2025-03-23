"""
tests/test_path_evaluator.py
----------------
This module contains tests for the PathEvaluator class.
"""

import pytest
from unittest.mock import Mock, patch
from neo4j import Driver

from core.workflow.state import WorkflowState
from core.workflow.evaluator import PathEvaluator

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
def evaluator(mock_driver, mock_state):
    """Create a PathEvaluator instance."""
    return PathEvaluator(mock_driver, mock_state)

def test_evaluate_simple_condition(evaluator):
    """Test evaluating a simple condition."""
    # Add test data to state
    evaluator.state.add_step_output("step1", {"value": 42})
    
    # Test various simple conditions
    conditions = [
        {
            "condition": "@{step1}.value == 42",
            "expected": True
        },
        {
            "condition": "@{step1}.value > 40",
            "expected": True
        },
        {
            "condition": "@{step1}.value < 40",
            "expected": False
        }
    ]
    
    for test_case in conditions:
        result = evaluator.evaluate_condition(test_case["condition"])
        assert result == test_case["expected"]

def test_evaluate_complex_condition(evaluator):
    """Test evaluating complex conditions with multiple variables."""
    # Add test data to state
    evaluator.state.add_step_output("step1", {"value": 42, "name": "test"})
    evaluator.state.add_step_output("step2", {"value": 24, "status": "complete"})
    
    # Test complex conditions
    conditions = [
        {
            "condition": "@{step1}.value > @{step2}.value and @{step2}.status == 'complete'",
            "expected": True
        },
        {
            "condition": "@{step1}.name == 'test' or @{step2}.value > 50",
            "expected": True
        },
        {
            "condition": "(@{step1}.value < @{step2}.value) and (@{step1}.name != 'test')",
            "expected": False
        }
    ]
    
    for test_case in conditions:
        result = evaluator.evaluate_condition(test_case["condition"])
        assert result == test_case["expected"]

def test_evaluate_with_missing_variables(evaluator):
    """Test evaluating conditions with missing variables."""
    # Add some test data
    evaluator.state.add_step_output("step1", {"value": 42})
    
    # Test condition with missing variable
    with pytest.raises(ValueError):
        evaluator.evaluate_condition("@{missing_step}.value > 0")

def test_evaluate_invalid_condition(evaluator):
    """Test evaluating invalid conditions."""
    invalid_conditions = [
        "invalid syntax >>>",
        "@{step1}.value ==",  # incomplete comparison
        "1 = 1"  # invalid operator
    ]
    
    for condition in invalid_conditions:
        with pytest.raises(ValueError):
            evaluator.evaluate_condition(condition)

def test_evaluate_path_conditions(evaluator):
    """Test evaluating path conditions."""
    # Add test data to state
    evaluator.state.add_step_output("step1", {"value": 42, "status": "complete"})
    evaluator.state.add_step_output("step2", {"value": 24, "type": "test"})
    
    # Define test paths with conditions
    paths = [
        {
            "conditions": [
                "@{step1}.value > 40",
                "@{step1}.status == 'complete'"
            ],
            "expected": True
        },
        {
            "conditions": [
                "@{step2}.value > 30",
                "@{step2}.type == 'test'"
            ],
            "expected": False
        }
    ]
    
    for test_case in paths:
        result = evaluator.evaluate_path_conditions(test_case["conditions"])
        assert result == test_case["expected"]

def test_evaluate_with_boolean_variables(evaluator):
    """Test evaluating conditions with boolean variables."""
    # Add test data with boolean values
    evaluator.state.add_step_output("step1", {"is_valid": True})
    evaluator.state.add_step_output("step2", {"is_complete": False})
    
    # Test conditions with boolean values
    conditions = [
        {
            "condition": "@{step1}.is_valid",
            "expected": True
        },
        {
            "condition": "not @{step2}.is_complete",
            "expected": True
        },
        {
            "condition": "@{step1}.is_valid and not @{step2}.is_complete",
            "expected": True
        }
    ]
    
    for test_case in conditions:
        result = evaluator.evaluate_condition(test_case["condition"])
        assert result == test_case["expected"]

def test_evaluate_with_list_operations(evaluator):
    """Test evaluating conditions with list operations."""
    # Add test data with lists
    evaluator.state.add_step_output("step1", {"values": [1, 2, 3]})
    evaluator.state.add_step_output("step2", {"items": ["a", "b", "c"]})
    
    # Test conditions with list operations
    conditions = [
        {
            "condition": "len(@{step1}.values) == 3",
            "expected": True
        },
        {
            "condition": "2 in @{step1}.values",
            "expected": True
        },
        {
            "condition": "'d' not in @{step2}.items",
            "expected": True
        }
    ]
    
    for test_case in conditions:
        result = evaluator.evaluate_condition(test_case["condition"])
        assert result == test_case["expected"] 