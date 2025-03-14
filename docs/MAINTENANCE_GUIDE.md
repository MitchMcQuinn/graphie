# Graphie Maintenance Guide

This guide provides instructions for maintaining and troubleshooting the Graphie application after the codebase consolidation and reorganization.

## Running the Application

The recommended way to start the application is to use the setup script:

```bash
./setup.sh
```

This script will:
1. Check for the `.env.local` file with Neo4j credentials
2. Update the Neo4j database with the workflow configuration
3. Clean up and verify the workflow
4. Install required dependencies
5. Start the application on port 5001

## Project Structure

After reorganization, the project uses the following structure:

- **Core Application:**
  - **app.py**: The main Flask application
  - **engine.py**: The synced workflow engine with variable synchronization
  - **fixed_engine.py**: The foundation engine that is extended by the synced version
  - **setup.sh**: The main script to set up and start the application

- **Utilities:**
  - **utils/**: Utility modules (analyze, request, fixed_reply, etc.)
  - **tools/**: Scripts for managing and updating the workflow, including:
    - **update_workflow_for_fixed_engine.py**: Updates Neo4j with workflow configuration
    - **check_and_clean_workflow.py**: Cleans up workflow configuration issues
    - **check_workflow_steps.py**: Verifies workflow configuration
    - **fix_show_analysis_node.py**: Fixes variable handling in analysis nodes

- **Documentation:**
  - **docs/**: Documentation files
  - **examples/**: Example workflow definitions in Cypher

- **Testing:**
  - **tests/**: Test and debugging scripts

## Troubleshooting

### Application Won't Start

If the application fails to start, check the following:

1. **Check for errors in the console output**:
   ```bash
   python app.py
   ```

2. **Verify Neo4j connection**:
   ```bash
   python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('$NEO4J_URL', auth=('$NEO4J_USERNAME', '$NEO4J_PASSWORD')); driver.verify_connectivity(); print('Neo4j connection successful')"
   ```

3. **Test if the application is running**:
   ```bash
   python tests/test_app_running.py
   ```

4. **Check for port conflicts**:
   ```bash
   lsof -i :5001
   ```

### "FixedWorkflowEngine.__init__() takes 1 positional argument but 2 were given"

If you see this error, it means there's an incompatibility between the SyncedWorkflowEngine and FixedWorkflowEngine classes:

1. Check the `__init__` method in `engine.py` to ensure it calls `super().__init__()` without arguments
2. Make sure it sets `self.max_parallel_paths` directly after calling the parent constructor

### Missing Variables in Workflow

If the workflow is failing to resolve variables:

1. Use the `/debug_variables` endpoint to check what variables are available
2. Check the `/stream_log` endpoint for real-time logging
3. Verify the workflow configuration in Neo4j

## Testing

To test if the application is running correctly:

```bash
python tests/test_app_running.py
```

For more comprehensive testing, access the debug endpoints:
- `/debug_workflow`: Overview of workflow state, paths, and deferred steps
- `/debug_variables`: Detailed view of variable availability
- `/stream_log`: Real-time logging

## Updating Workflows

To update the workflow configuration:

1. Modify the appropriate update script (e.g., `tools/update_workflow_for_fixed_engine.py`)
2. Run the update script:
   ```bash
   python tools/update_workflow_for_fixed_engine.py
   ```
3. Clean up the workflow:
   ```bash
   python tools/check_and_clean_workflow.py
   ```
4. Verify the workflow:
   ```bash
   python tools/check_workflow_steps.py
   ``` 