from graph_engine import get_graph_workflow_engine
import logging
import json
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_workflow():
    """Test workflow execution from start to finish"""
    try:
        # Get the graph workflow engine
        engine = get_graph_workflow_engine()
        
        # Create a new session
        session_id = engine.create_session()
        logger.info(f"Created new session: {session_id}")
        
        # Start the workflow
        logger.info("Starting workflow")
        result = engine.start_workflow(session_id)
        logger.info(f"Start workflow result: {result}")
        
        # Check session status after starting
        status = engine.get_session_status(session_id)
        logger.info(f"Session status after starting: {status}")
        
        # If awaiting input, provide a test response
        if status.get('status') == 'awaiting_input':
            logger.info("Workflow is awaiting input, providing test response")
            test_input = "Tell me about artificial intelligence"
            result = engine.continue_workflow(test_input, session_id)
            logger.info(f"Continue workflow result: {result}")
            
            # Check status again
            status = engine.get_session_status(session_id)
            logger.info(f"Session status after input: {status}")
            
            # Get frontend state
            frontend_state = engine.get_frontend_state(session_id)
            logger.info(f"Frontend state: {frontend_state}")
        
        # Brief pause to allow processing
        logger.info("Waiting for processing...")
        time.sleep(3)
        
        # Final check of session status
        status = engine.get_session_status(session_id)
        logger.info(f"Final session status: {status}")
        
        # Final check of memory
        try:
            memory = status.get('memory', {})
            logger.info("\n===== MEMORY SUMMARY =====")
            for step_id, outputs in memory.items():
                logger.info(f"Step {step_id}: {len(outputs)} outputs")
                if outputs and isinstance(outputs[-1], dict):
                    for key, value in outputs[-1].items():
                        if isinstance(value, str) and len(value) > 50:
                            logger.info(f"  {key}: {value[:50]}...")
                        else:
                            logger.info(f"  {key}: {value}")
        except Exception as e:
            logger.error(f"Error summarizing memory: {str(e)}")
        
        return session_id
    except Exception as e:
        logger.error(f"Error testing workflow: {str(e)}")
        return None

if __name__ == "__main__":
    test_workflow() 