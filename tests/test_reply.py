"""
Tests for the reply module.
"""

import pytest
from unittest.mock import Mock, patch
from utils.reply import reply

@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    return Mock()

@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = Mock()
    manager.get_session_status.return_value = {'next_steps': ['test-step']}
    manager.store_memory.return_value = None
    manager.add_assistant_message.return_value = None
    manager.set_session_status.return_value = None
    return manager

@pytest.fixture
def mock_session():
    """Create a mock session."""
    return {'id': 'test-session-id'}

def test_reply_with_simple_text(mock_driver, mock_session_manager, mock_session):
    """Test reply with simple text input."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager):
        
        input_data = {'response': 'Hello, world!'}
        result = reply(mock_session, input_data)
        
        assert result['reply'] == 'Hello, world!'
        mock_session_manager.store_memory.assert_called_once()
        mock_session_manager.add_assistant_message.assert_called_once()

def test_reply_with_variable_reference(mock_driver, mock_session_manager, mock_session):
    """Test reply with variable reference."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager), \
         patch('utils.reply.resolve_variable', return_value='resolved_value'):
        
        input_data = {'response': 'Value: @{test-session-id.test-step.value}'}
        result = reply(mock_session, input_data)
        
        assert 'resolved_value' in result['reply']
        mock_session_manager.store_memory.assert_called_once()

def test_reply_with_multiple_variables(mock_driver, mock_session_manager, mock_session):
    """Test reply with multiple variable references."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager), \
         patch('utils.reply.resolve_variable', side_effect=['value1', 'value2']):
        
        input_data = {
            'response': 'First: @{test-session-id.test-step.value1}, Second: @{test-session-id.test-step.value2}'
        }
        result = reply(mock_session, input_data)
        
        assert 'value1' in result['reply']
        assert 'value2' in result['reply']

def test_reply_with_malformed_variable(mock_driver, mock_session_manager, mock_session):
    """Test reply with malformed variable reference."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager):
        
        input_data = {'response': 'Malformed: @{test-session-id.test-step.value'}
        result = reply(mock_session, input_data)
        
        assert 'Malformed: @{test-session-id.test-step.value' in result['reply']

def test_reply_with_variable_resolution_error(mock_driver, mock_session_manager, mock_session):
    """Test reply when variable resolution fails."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager), \
         patch('utils.reply.resolve_variable', side_effect=Exception('Resolution failed')):
        
        input_data = {'response': 'Error: @{test-session-id.test-step.value}'}
        result = reply(mock_session, input_data)
        
        assert '@{test-session-id.test-step.value}' in result['reply']

def test_reply_with_empty_input(mock_driver, mock_session_manager, mock_session):
    """Test reply with empty input."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager):
        
        input_data = {'response': ''}
        result = reply(mock_session, input_data)
        
        assert 'I\'m sorry' in result['reply']  # Should use fallback message

def test_reply_with_session_manager_error(mock_driver, mock_session_manager, mock_session):
    """Test reply when session manager operations fail."""
    mock_session_manager.store_memory.side_effect = Exception('Storage failed')
    
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager):
        
        input_data = {'response': 'Test message'}
        result = reply(mock_session, input_data)
        
        assert result['reply'] == 'Test message'  # Should still return the message even if storage fails

def test_reply_with_mixed_content(mock_driver, mock_session_manager, mock_session):
    """Test reply with mixed text and variable content."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager), \
         patch('utils.reply.resolve_variable', return_value='resolved'):
        
        input_data = {
            'response': 'Text before @{test-session-id.test-step.value} and after'
        }
        result = reply(mock_session, input_data)
        
        assert 'Text before' in result['reply']
        assert 'resolved' in result['reply']
        assert 'and after' in result['reply']

def test_reply_with_simple_session_id(mock_driver, mock_session_manager, mock_session):
    """Test reply with simple session ID reference."""
    with patch('utils.reply.get_neo4j_driver', return_value=mock_driver), \
         patch('utils.reply.get_session_manager', return_value=mock_session_manager):
        
        input_data = {'response': 'Session: @{test-session-id}'}
        result = reply(mock_session, input_data)
        
        assert 'test-session-id' in result['reply']
        mock_session_manager.store_memory.assert_called_once() 