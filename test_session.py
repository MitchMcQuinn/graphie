from graph_engine import GraphWorkflowEngine
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_session_creation():
    """Test creating a session and checking if it exists"""
    try:
        # Create engine
        engine = GraphWorkflowEngine()
        
        # Create a session
        session_id = engine.create_session()
        logger.info(f"Created session with ID: {session_id}")
        
        # Check if the session exists
        exists = engine.has_session(session_id)
        logger.info(f"Session exists: {exists}")
        
        # Get session status
        status = engine.get_session_status(session_id)
        logger.info(f"Session status: {status}")
        
        return session_id
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return None

if __name__ == "__main__":
    test_session_creation() 