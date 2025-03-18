from graph_engine import get_graph_workflow_engine
import logging
import json
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def examine_session(session_id=None):
    """Examine a specific session in detail"""
    try:
        # Get the graph workflow engine
        engine = get_graph_workflow_engine()
        
        # If no session_id provided, find an interesting one
        if not session_id:
            with engine.driver.session() as session:
                # First look for a session that's awaiting input
                result = session.run("""
                    MATCH (s:SESSION) 
                    WHERE s.status = 'awaiting_input'
                    RETURN s.id as id
                    LIMIT 1
                """)
                
                record = result.single()
                if record:
                    session_id = record["id"]
                    logger.info(f"Using awaiting_input session: {session_id}")
                else:
                    # Otherwise get any session with memory
                    result = session.run("""
                        MATCH (s:SESSION)
                        WHERE s.memory IS NOT NULL AND s.memory <> '{}'
                        RETURN s.id as id
                        LIMIT 1
                    """)
                    
                    record = result.single()
                    if record:
                        session_id = record["id"]
                        logger.info(f"Using session with memory: {session_id}")
                    else:
                        # Lastly, just get any session
                        result = session.run("""
                            MATCH (s:SESSION)
                            RETURN s.id as id
                            LIMIT 1
                        """)
                        
                        record = result.single()
                        if record:
                            session_id = record["id"]
                            logger.info(f"Using first found session: {session_id}")
                        else:
                            logger.error("No sessions found in database")
                            return
        
        # Now examine the session in detail
        with engine.driver.session() as session:
            # Get session data
            result = session.run("""
                MATCH (s:SESSION {id: $session_id})
                RETURN s.status as status, 
                       s.next_steps as next_steps,
                       s.memory as memory,
                       s.chat_history as chat_history,
                       s.errors as errors,
                       s.created_at as created_at
            """, session_id=session_id)
            
            record = result.single()
            if not record:
                logger.error(f"Session {session_id} not found")
                return
            
            logger.info(f"===== SESSION {session_id} =====")
            logger.info(f"Status: {record['status']}")
            logger.info(f"Next steps: {record['next_steps']}")
            logger.info(f"Created at: {record['created_at']}")
            
            # Examine memory in detail
            try:
                memory_str = record['memory'] if record['memory'] else "{}"
                memory = json.loads(memory_str)
                
                logger.info("\n===== MEMORY =====")
                logger.info(f"Memory contains {len(memory)} steps")
                
                for step_id, outputs in memory.items():
                    logger.info(f"\nStep: {step_id}")
                    logger.info(f"Outputs: {len(outputs)}")
                    
                    # Show all outputs for this step
                    for i, output in enumerate(outputs):
                        logger.info(f"  Output {i+1}:")
                        if isinstance(output, dict):
                            for key, value in output.items():
                                value_str = str(value)
                                if len(value_str) > 100:
                                    value_str = value_str[:100] + "..."
                                logger.info(f"    {key}: {value_str}")
                        else:
                            logger.info(f"    {str(output)[:100]}...")
            except Exception as e:
                logger.error(f"Error parsing memory: {str(e)}")
            
            # Examine chat history
            try:
                chat_history_str = record['chat_history'] if record['chat_history'] else "[]"
                chat_history = json.loads(chat_history_str)
                
                logger.info("\n===== CHAT HISTORY =====")
                logger.info(f"Chat history contains {len(chat_history)} messages")
                
                for i, message in enumerate(chat_history):
                    logger.info(f"Message {i+1}:")
                    if isinstance(message, dict):
                        role = message.get('role', 'unknown')
                        content = message.get('content', '')
                        logger.info(f"  Role: {role}")
                        logger.info(f"  Content: {content[:100]}..." if len(content) > 100 else f"  Content: {content}")
                    else:
                        logger.info(f"  {str(message)[:100]}...")
            except Exception as e:
                logger.error(f"Error parsing chat history: {str(e)}")
            
            # Examine errors
            try:
                errors_str = record['errors'] if record['errors'] else "[]"
                errors = json.loads(errors_str)
                
                logger.info("\n===== ERRORS =====")
                logger.info(f"Errors contains {len(errors)} items")
                
                for i, error in enumerate(errors):
                    logger.info(f"Error {i+1}:")
                    if isinstance(error, dict):
                        for key, value in error.items():
                            logger.info(f"  {key}: {value}")
                    else:
                        logger.info(f"  {str(error)}")
            except Exception as e:
                logger.error(f"Error parsing errors: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error examining session: {str(e)}")

if __name__ == "__main__":
    # Use session ID from command line if provided
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    examine_session(session_id) 