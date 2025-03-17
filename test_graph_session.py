"""
test_graph_session.py
-------------------
This script tests the new graph-based session management functionality.

It creates a session, runs a simple workflow, and verifies that the SESSION
node is properly created and updated.
"""

import os
import json
import logging
from dotenv import load_dotenv
from graph_engine import get_graph_workflow_engine
from engine import get_neo4j_driver

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

def test_create_session():
    """Test creating a SESSION node"""
    engine = get_graph_workflow_engine()
    session_id = engine.create_session()
    
    print(f"Created session with ID: {session_id}")
    
    # Verify session exists
    exists = engine.has_session(session_id)
    print(f"Session exists: {exists}")
    
    return session_id

def test_run_workflow(session_id):
    """Test running a workflow"""
    engine = get_graph_workflow_engine()
    
    print(f"Starting workflow for session {session_id}")
    result = engine.start_workflow(session_id)
    print(f"Start workflow result: {result}")
    
    # Get frontend state
    state = engine.get_frontend_state(session_id)
    print(f"Frontend state: {json.dumps(state, indent=2)}")
    
    return state

def test_variable_resolution():
    """Test variable resolution with the new format"""
    from utils.resolve_variable import resolve_variable
    
    engine = get_graph_workflow_engine()
    session_id = engine.create_session()
    
    # First, store some data
    driver = get_neo4j_driver()
    with driver.session() as db_session:
        db_session.run("""
            MATCH (s:SESSION {id: $session_id})
            SET s.memory = {
                'test-step': [{
                    'message': 'Hello, world!',
                    'count': 42,
                    'nested': {'value': 'nested value'}
                }]
            }
        """, session_id=session_id)
    
    # Test variable resolution
    tests = [
        f"@{{{session_id}}}.test-step.message",
        f"@{{{session_id}}}.test-step.count",
        f"@{{{session_id}}}.test-step.nested",
        f"@{{{session_id}}}.test-step.missing|default",
        f"@{{{session_id}}}.missing-step.value|not found"
    ]
    
    for test in tests:
        value = resolve_variable(driver, session_id, test)
        print(f"Resolved {test} to: {value}")
    
    return session_id

def verify_session_structure(session_id):
    """Verify the SESSION node structure in Neo4j"""
    driver = get_neo4j_driver()
    with driver.session() as db_session:
        result = db_session.run("""
            MATCH (s:SESSION {id: $session_id})
            RETURN s
        """, session_id=session_id)
        
        record = result.single()
        if record:
            session_node = dict(record['s'])
            print(f"SESSION node properties:")
            for key, value in session_node.items():
                print(f"  {key}: {value}")
            
            return session_node
        else:
            print(f"SESSION node with ID {session_id} not found")
            return None

def main():
    """Run tests"""
    print("Testing graph-based session management")
    
    # Test creating a session
    session_id = test_create_session()
    
    # Test variable resolution
    print("\nTesting variable resolution")
    var_session_id = test_variable_resolution()
    
    # Test running a workflow
    print("\nTesting workflow execution")
    test_run_workflow(session_id)
    
    # Verify session structure
    print("\nVerifying SESSION node structure")
    verify_session_structure(session_id)

if __name__ == "__main__":
    main() 