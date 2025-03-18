#!/usr/bin/env python
"""
prepare_graph_sessions.py
-----------------------
Master integration script that prepares a Graphie environment for using
the graph-based session management system. Performs all necessary steps:

1. Sets up Neo4j schema for SESSION nodes
2. Updates workflow variable references to the new format
3. Applies run-time patches for variable resolution
4. Tests the update with a workflow simulation
5. Reports on update status

Usage:
    python prepare_graph_sessions.py [--skip-schema] [--skip-update] [--skip-test]
"""

import os
import sys
import argparse
import logging
import subprocess
from dotenv import load_dotenv
from engine import get_neo4j_driver

# Add the current directory to Python path so modules can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_neo4j_schema(driver):
    """Set up Neo4j schema for SESSION nodes using the setup script"""
    logger.info("Setting up Neo4j schema for SESSION nodes...")
    
    try:
        # Check if setup_neo4j.cypher exists
        if not os.path.exists('setup_neo4j.cypher'):
            logger.error("setup_neo4j.cypher not found. Cannot set up Neo4j schema.")
            return False
        
        # Execute the Cypher script directly using the driver
        with open('setup_neo4j.cypher', 'r') as f:
            setup_script = f.read()
            
        with driver.session() as session:
            # Execute each statement separately (crude split by ;)
            statements = [stmt.strip() for stmt in setup_script.split(';') if stmt.strip()]
            
            for i, stmt in enumerate(statements, 1):
                if stmt.strip():
                    logger.info(f"Executing statement {i}/{len(statements)}")
                    session.run(stmt)
            
            logger.info("Neo4j schema setup complete")
            
            # Verify the schema was created
            try:
                constraint_result = session.run("""
                    SHOW CONSTRAINTS WHERE name = 'session_id_unique'
                """)
                
                if not list(constraint_result):
                    logger.warning("SESSION ID constraint not found. Schema setup may have failed.")
                    return False
            except Exception as e:
                # Some Neo4j versions may not support SHOW CONSTRAINTS
                logger.warning(f"Could not verify constraint: {str(e)}")
                
            return True
    
    except Exception as e:
        logger.error(f"Error setting up Neo4j schema: {str(e)}")
        return False

def run_update_workflow():
    """Run the workflow update script"""
    logger.info("Updating workflow variable references...")
    
    try:
        # Import and run the update_workflow module
        from update_workflow import update_workflow
        
        result = update_workflow()
        if not result:
            logger.error("Workflow update failed.")
            return False
        
        logger.info(f"Workflow update complete: {result}")
        return True
    
    except ImportError:
        logger.error("update_workflow.py module not found.")
        return False
    except Exception as e:
        logger.error(f"Error running workflow update: {str(e)}")
        return False

def apply_variable_resolver_patch():
    """Apply the variable resolver patch for runtime compatibility"""
    logger.info("Applying variable resolver patch...")
    
    try:
        # Import and run the variable resolver patch
        from variable_resolver import patch_graph_engine
        
        result = patch_graph_engine()
        if not result:
            logger.warning("Variable resolver patch could not be applied.")
            logger.warning("Ensure you restart the application for changes to take effect.")
            return False
        
        logger.info(f"Variable resolver patch applied: {result}")
        return True
    
    except ImportError:
        logger.error("variable_resolver.py module not found.")
        return False
    except Exception as e:
        logger.error(f"Error applying variable resolver patch: {str(e)}")
        return False

def run_workflow_test():
    """Run a test of the updated workflow"""
    logger.info("Running workflow test...")
    
    try:
        # Import and run the test_updated_workflow module
        from test_updated_workflow import test_workflow_execution
        
        test_workflow_execution()
        logger.info("Workflow test complete")
        return True
    
    except ImportError:
        logger.error("test_updated_workflow.py module not found.")
        return False
    except Exception as e:
        logger.error(f"Error running workflow test: {str(e)}")
        return False

def check_status():
    """Check the status of the workflow update"""
    logger.info("Checking workflow update status...")
    
    try:
        # First check if the module file exists
        if not os.path.exists('check_workflow_update_status.py'):
            logger.error("check_workflow_update_status.py file not found.")
            return False
            
        # Import and run the check_workflow_update_status module
        try:
            from check_workflow_update_status import check_update_status
            
            results = check_update_status()
            if not results:
                logger.error("Failed to check workflow update status.")
                return False
            
            logger.info(f"Status check complete: {results['updated_nodes']}/{results['nodes_with_variables']} nodes updated")
            return True
        except ImportError:
            logger.error("Could not import check_workflow_update_status. Trying direct execution...")
            
            # Try to execute it as a separate process
            result = subprocess.run([sys.executable, 'check_workflow_update_status.py'], 
                                   capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Status check completed via subprocess")
                logger.info(result.stdout)
                return True
            else:
                logger.error(f"Status check subprocess failed: {result.stderr}")
                return False
    
    except Exception as e:
        logger.error(f"Error checking workflow update status: {str(e)}")
        return False

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Prepare Graphie for graph-based session management")
    parser.add_argument('--skip-schema', action='store_true', help="Skip Neo4j schema setup")
    parser.add_argument('--skip-update', action='store_true', help="Skip workflow update")
    parser.add_argument('--skip-test', action='store_true', help="Skip workflow test")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv('.env.local')
    
    logger.info("Starting graph session preparation...")
    
    # Connect to Neo4j
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Failed to connect to Neo4j. Ensure NEO4J_* environment variables are set correctly.")
        sys.exit(1)
    
    # Step 1: Set up Neo4j schema
    if not args.skip_schema:
        if not setup_neo4j_schema(driver):
            logger.error("Neo4j schema setup failed. Continuing with other steps...")
    else:
        logger.info("Skipping Neo4j schema setup")
    
    # Step 2: Update workflow variable references
    if not args.skip_update:
        if not run_update_workflow():
            logger.error("Workflow update failed. Continuing with other steps...")
    else:
        logger.info("Skipping workflow update")
    
    # Step 3: Apply variable resolver patch
    if not apply_variable_resolver_patch():
        logger.warning("Variable resolver patch could not be applied. Runtime functionality may be affected.")
    
    # Step 4: Run workflow test
    if not args.skip_test:
        if not run_workflow_test():
            logger.error("Workflow test failed. System may not be ready for production use.")
    else:
        logger.info("Skipping workflow test")
    
    # Step 5: Check update status
    check_status()
    
    logger.info("Graph session preparation complete!")
    logger.info("Restart your application for changes to take effect.")

if __name__ == "__main__":
    main() 