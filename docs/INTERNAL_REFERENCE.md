# Graphie Internal Reference Document

This document serves as a comprehensive technical reference for the Graphie project, designed to provide quick context for troubleshooting and understanding the system architecture.

## System Architecture Overview

Graphie is a Neo4j-powered conversational workflow engine built on a modular architecture designed to process parallel workflow paths with synchronized variable handling.

### Core Components Relationship Diagram

```
┌───────────────┐     ┌───────────────────┐     ┌───────────────┐
│  Flask App    │◄────┤ Synced Workflow   │◄────┤  Neo4j Graph  │
│  (app.py)     │     │ Engine (engine.py)│     │   Database    │
└───────┬───────┘     └─────────┬─────────┘     └───────────────┘
        │                       │                        ▲
        │                       │                        │
        ▼                       ▼                        │
┌───────────────┐     ┌───────────────────┐     ┌───────────────┐
│ Web Interface │     │  Utility Modules  │     │ Workflow Mgmt │
│ (templates)   │     │    (utils/)       │─────┤ Scripts       │
└───────────────┘     └───────────────────┘     │ (tools/)      │
                                                └───────────────┘
```

## Core Files and Their Functions

### 1. Workflow Engine Components

#### `engine.py` (293 lines)
- **Purpose**: Implements the `SyncedWorkflowEngine` class, enhancing the fixed engine with variable synchronization and deferred step processing
- **Key Features**:
  - Indefinite variable readiness checks
  - Deferred step processing through threading
  - Automatic retries for unresolved variables
  - Session state management
- **Key Methods**:
  - `_replace_variables()`: Enhanced variable resolution with missing variable detection
  - `_process_step()`: Processes steps with failure handling for unresolved variables
  - `_retry_deferred_step()`: Background retry mechanism for deferred steps
  - `mark_session_inactive()`: Stops retry attempts when sessions end
- **Dependencies**: Extends `FixedWorkflowEngine` from `fixed_engine.py`

#### `fixed_engine.py` (592 lines)
- **Purpose**: Provides the foundation engine with parallel path processing capabilities
- **Key Features**:
  - Parallel workflow path processing
  - Neo4j database integration for workflow definition
  - Variable replacement in step parameters
  - Dynamic function loading from utility modules
- **Key Methods**:
  - `initialize_workflow()`: Loads the workflow from Neo4j
  - `process_workflow()`: Main entry point for workflow execution
  - `process_parallel_paths()`: Manages multiple workflow branches
  - `_execute_step_function()`: Dynamically executes functions based on workflow steps
- **Dependencies**: Neo4j database, utility modules in `utils/`

### 2. Web Application Components

#### `app.py` (368 lines)
- **Purpose**: Flask application providing the web interface and API endpoints for the workflow engine
- **Key Features**:
  - Chat interface for user interaction
  - Session management
  - Debugging endpoints for workflow monitoring
  - SocketIO integration for real-time updates
- **Key Routes**:
  - `/`: Main chat interface
  - `/start_chat`: Initializes a new chat session
  - `/send_message`: Processes user messages
  - `/continue_processing`: Handles workflow continuation
  - `/debug_workflow` and `/debug_variables`: Debugging endpoints
  - `/stream_log`: Real-time log streaming
- **Dependencies**: Flask, SocketIO, `engine.py`, templates

#### `templates/index.html` (481 lines)
- **Purpose**: Provides the user interface for the chat application
- **Key Features**:
  - Chat message display
  - Input form for user messages
  - Responsive design
  - Debug panel for workflow visualization
- **Dependencies**: JavaScript for frontend interaction, CSS for styling

### 3. Utility Modules (in `utils/`)

#### `analyze.py` (143 lines)
- **Purpose**: Provides custom functions for analyzing user input
- **Key Functions**:
  - `analyze_input()`: Extracts entities and sentiment from text
  - `extract_animal()`: Identifies animal names in text
  - `analyze_sentiment()`: Determines positive/negative sentiment

#### `condition.py` (167 lines)
- **Purpose**: Implements conditional logic for workflow branching
- **Key Functions**:
  - `equals()`: Checks if values match
  - `not_equals()`: Checks if values don't match
  - `contains()`: Checks if a value contains a substring

#### `fixed_reply.py` (111 lines)
- **Purpose**: Provides functions for generating fixed replies
- **Key Function**: `fixed_reply()`: Returns predefined responses

#### `generate.py` (474 lines)
- **Purpose**: Handles AI-generated content using OpenAI's API
- **Key Function**: `generate()`: Creates AI responses based on prompts

#### `rate_limiter.py` (201 lines)
- **Purpose**: Manages API rate limiting for external services
- **Key Function**: `limit_api_calls()`: Throttles API requests

#### `reply.py` (102 lines)
- **Purpose**: Manages replies to the user
- **Key Function**: `reply()`: Formats and sends responses to users

#### `request.py` (86 lines)
- **Purpose**: Handles user input requests
- **Key Function**: `request()`: Captures and processes user input

#### `structured_generation.py` (119 lines)
- **Purpose**: Provides structured generation capabilities
- **Key Function**: `structured_generation()`: Generates structured content following specific formats

### 4. Workflow Management Tools (in `tools/`)

#### `update_workflow_for_fixed_engine.py` (293 lines)
- **Purpose**: Updates the Neo4j database with the workflow configuration
- **Key Function**: Creates and connects workflow nodes in Neo4j

#### `check_and_clean_workflow.py` (172 lines)
- **Purpose**: Cleans up workflow configuration issues
- **Key Features**:
  - Fixes incorrect function references
  - Updates variable references
  - Checks for isolated nodes
  - Verifies node relationships

#### `check_workflow_steps.py` (130 lines)
- **Purpose**: Verifies workflow configuration correctness
- **Key Features**:
  - Lists all workflow steps
  - Verifies function references
  - Checks relationships between nodes
  - Identifies paths in the workflow

#### `fix_show_analysis_node.py` (65 lines)
- **Purpose**: Specifically fixes variable handling in analysis nodes
- **Key Features**: Updates variable references in analysis nodes

#### `update_parallel_workflow.py` (158 lines)
- **Purpose**: Updates workflow configuration for parallel processing
- **Key Features**: Configures workflows for parallel path execution

#### `update_workflow.py` (133 lines)
- **Purpose**: Basic workflow update utility
- **Key Features**: Updates basic workflow structures in Neo4j

## Data Flow and Process Logic

### Initialization Process
1. `setup.sh` runs and updates the Neo4j database with workflow configuration
2. `app.py` initializes the `SyncedWorkflowEngine` from `engine.py`
3. The engine connects to Neo4j and loads the workflow definition

### Request Processing Flow
1. User interacts with the web interface (`index.html`)
2. `app.py` routes handle requests and manage sessions
3. `engine.py` processes the workflow based on user input:
   - Identifies the next steps in the workflow
   - Processes multiple paths in parallel
   - Handles variable dependencies and deferred steps
4. Utility modules (`utils/`) perform specific functions based on workflow nodes
5. Results are stored in the session and returned to the user interface

### Variable Synchronization Process
1. When a step references unavailable variables, it's deferred
2. A background thread is scheduled to retry the step
3. Other workflow paths continue executing in parallel
4. When required variables become available, deferred steps are processed
5. This cycle continues until the workflow completes or the session ends

## Current Workflow Implementation

The current workflow implementation in Neo4j consists of the following key nodes:

### Core Workflow Nodes

1. **`root`**: Starting point of the workflow
   - Function: `reply.reply`
   - Purpose: Welcomes the user to the conversation

2. **`get-input`**: Captures user input
   - Function: `request.request`
   - Purpose: Asks the user to enter a message containing an animal name

3. **`extract-animal`**: Analyzes input for animal names
   - Function: `analyze.analyze_input`
   - Input: Uses the `extract_animal_names` function on user input
   - Stores: Animal names in the `animals` variable

4. **`analyze-input`**: Analyzes input for sentiment
   - Function: `analyze.analyze_input`
   - Input: Uses the `sentiment_analysis` function on user input
   - Stores: Sentiment analysis in the `sentiment` variable

5. **`return-animal`**: Creates a response about the mentioned animal
   - Function: `fixed_reply.fixed_reply`
   - Input: References both `@{extract-animal}.animals` and `@{analyze-input}.sentiment`
   - Purpose: Demonstrates variable synchronization between parallel paths

6. **`continue-question`**: Asks if the user wants to continue
   - Function: `request.request`
   - Purpose: Creates a loop in the conversation flow

7. **`show-analysis`**: Shows detailed analysis results
   - Function: `fixed_reply.fixed_reply`
   - Input: References various analysis results
   - Purpose: Displays comprehensive analysis of user input

### Workflow Structure

The workflow is structured with parallel paths that demonstrate the variable synchronization capabilities:

1. After `get-input`, the workflow branches into parallel paths:
   - Path 1: `extract-animal` → `return-animal`
   - Path 2: `analyze-input` → (contributes to `return-animal`)

2. The `return-animal` node depends on both paths, demonstrating synchronized variable handling:
   - It requires `@{extract-animal}.animals` from Path 1
   - It requires `@{analyze-input}.sentiment` from Path 2

3. The workflow includes a loop structure:
   - `continue-question` can loop back to `get-input` based on user response

### Variable References

Key variable references in the workflow:

- `@{get-input}.user_input`: User's input message
- `@{extract-animal}.animals`: Extracted animal names
- `@{analyze-input}.sentiment`: Sentiment analysis of user input

### Error Handling

The workflow includes error handling for:
- Missing animal names
- Failed analysis
- Connection issues

## Key Concepts

### Workflow Nodes
- Represented as STEP nodes in Neo4j
- Properties include id, description, function, and input
- Core building blocks of conversational flows

### Workflow Relationships
- Represented as NEXT relationships in Neo4j
- Connect steps to define the flow
- Can include conditional functions for branching logic

### Variable References
- Format: `@{node-id}.key`
- Used to access values from previous workflow steps
- Can include default values: `@{node-id}.key|default_value`

### Parallel Paths
- Multiple workflow branches executing simultaneously
- Managed by the `process_parallel_paths()` method
- Limited by `max_parallel_paths` parameter (default: 5)

### Deferred Steps
- Steps that can't execute due to missing variable references
- Tracked in the `deferred_steps` dictionary
- Automatically retried at intervals defined by `retry_delay`

## Troubleshooting Patterns

### 1. Workflow Not Progressing
- **Check**: Debugging endpoints `/debug_workflow` and `/debug_variables`
- **Look for**: Deferred steps with missing variable references
- **Solution**: Verify workflow node relationships and function references

### 2. Function Reference Errors
- **Check**: Console logs for import errors
- **Look for**: Module not found or attribute errors
- **Solution**: Verify that utility modules exist and are properly referenced in workflow nodes

### 3. Variable Reference Issues
- **Check**: `/debug_variables` endpoint
- **Look for**: Missing or incorrect variable references
- **Solution**: Update workflow nodes to use the correct variable references

### 4. Infinite Loop Detection
- **Check**: `/stream_log` for repeated processing of the same nodes
- **Look for**: Steps being processed multiple times without progression
- **Solution**: Verify exit conditions in loop structures

### 5. Performance Issues
- **Check**: Execution time logs in the console
- **Look for**: Excessive deferred step retries or large numbers of parallel paths
- **Solution**: Adjust `retry_delay` and `max_parallel_paths` parameters

### 6. Common Workflow-Specific Issues

- **Issue**: `analyze.analyze_input` function not found
  - **Check**: Verify that `analyze.py` is in the `utils/` directory
  - **Solution**: Restore or create the proper analyze.py file

- **Issue**: Animal extraction not working
  - **Check**: Debug the `extract_animal_names` function in `analyze.py`
  - **Solution**: Update the animal detection logic

- **Issue**: Workflow stuck after user input
  - **Check**: Look for deferred steps waiting for variables
  - **Solution**: Check that both `extract-animal` and `analyze-input` are properly executing

## Neo4j Database Structure

### Node Labels
- `STEP`: Workflow steps with function references

### Relationship Types
- `NEXT`: Connections between workflow steps

### Common Queries
- Get all workflow steps:
  ```cypher
  MATCH (s:STEP) RETURN s
  ```
- Find isolated nodes:
  ```cypher
  MATCH (s:STEP) 
  WHERE NOT (s)-[:NEXT]->() AND NOT ()-[:NEXT]->(s)
  RETURN s
  ```
- Check relationships:
  ```cypher
  MATCH p=()-[r:NEXT]->() RETURN p
  ```

## File Dependencies and Interactions

```
app.py
├── engine.py
│   └── fixed_engine.py
│       └── neo4j database
├── utils/*.py (dynamically loaded)
└── templates/index.html

tools/*.py
└── neo4j database
```

## Testing and Verification

### Verification Script
- `tests/verify_project_structure.py`: Comprehensive project verification
- Checks for required directories, files, and application functionality

### Testing Endpoints
- `/debug_workflow`: Shows the current workflow state
- `/debug_variables`: Shows variable availability
- `/stream_log`: Provides real-time logging information

## Common Development Tasks

### 1. Adding a New Utility Function
1. Create a new function in an existing utility module or a new module in `utils/`
2. Ensure the function accepts `session` and `input_data` parameters
3. Store results in the session with consistent key naming
4. Update Neo4j workflow nodes to reference the new function

### 2. Updating the Workflow Structure
1. Modify the appropriate update script in `tools/`
2. Run the update script to apply changes to Neo4j
3. Use verification tools to ensure the workflow is properly configured

### 3. Debugging Workflow Issues
1. Use `/debug_workflow` to identify active paths and deferred steps
2. Use `/debug_variables` to check variable availability
3. Use `/stream_log` to monitor real-time execution
4. Check console logs for errors in function execution

### 4. Performance Optimization
1. Adjust `max_parallel_paths` in engine initialization
2. Modify `retry_delay` for deferred step retry frequency
3. Optimize heavy utility functions, especially those in frequently used paths

## Configuration

### Environment Variables (in `.env.local`)
- `NEO4J_URL`: Neo4j database URL
- `NEO4J_USERNAME`: Neo4j username
- `NEO4J_PASSWORD`: Neo4j password
- `OPENAI_API_KEY`: OpenAI API key for AI-generated responses
- `FLASK_SECRET_KEY`: Secret key for Flask session management

## Critical Implementation Decisions

### 1. Synced Engine Design
- Builds on top of `FixedWorkflowEngine` to add variable synchronization
- Uses threading for non-blocking retry behavior
- Indefinite retry mechanism tied to session state

### 2. Parallel Path Processing
- Maximum of 5 parallel paths by default
- Uses a queue-based approach to manage path processing
- Path management lives in the FixedWorkflowEngine class

### 3. Variable Handling
- Variable references detected using regex pattern `@{([^}]+)}.([^}\s|]+)(?:\|([^}]*))?`
- Supports default values with the `|` separator
- Missing variables trigger deferral in the synced engine

### 4. Dynamic Function Loading
- Functions referenced in workflow nodes are dynamically imported
- Format: `module_name.function_name` (e.g., `analyze.analyze_input`)
- Input data is passed as JSON and parsed into parameters

## Major Resolved Issues and Their Solutions

### 1. Incorrect Function References in Workflow

**Problem**: The workflow was using `utils.structured_generation.analyze_input` instead of the custom `analyze.analyze_input`.

**Solution**: 
- Created a custom `analyze.py` module with functions for extracting animal names and performing sentiment analysis.
- Implemented `check_and_clean_workflow.py` to automatically fix incorrect function references in the workflow.
- Confirmed proper function references via `check_workflow_steps.py`.

### 2. Variable Reference Issues

**Problem**: The `return-animal` node had incorrect variable references, causing it to not display proper animal names.

**Solution**:
- Fixed the variable references to correctly point to `@{extract-animal}.animals`.
- Implemented `fix_show_analysis_node.py` to specifically update variable handling in analysis nodes.
- Enhanced error detection in the engine to provide better feedback on missing variables.

### 3. Deadlock in Parallel Execution

**Problem**: Parallel paths sometimes reached deadlock when waiting for variables from each other.

**Solution**:
- Implemented the synchronized engine with deferred step processing.
- Added indefinite retry logic to continue attempting variable resolution as long as the session is active.
- Created a non-blocking architecture using threading to prevent UI freezes during retry cycles.

### 4. Constructor Compatibility Issues

**Problem**: `SyncedWorkflowEngine.__init__() takes 1 positional argument but 2 were given` error due to parameter incompatibility.

**Solution**:
- Modified the `SyncedWorkflowEngine` constructor to call the parent constructor without arguments.
- Added direct property assignment for configuration parameters after parent constructor call.
- Created a verification script to test for this specific issue.

### 5. Process Management Problems

**Problem**: Multiple instances of the application running simultaneously caused port conflicts.

**Solution**:
- Added process cleanup in the setup script to kill any existing instances.
- Implemented better logging to track application status.
- Created more robust startup procedures that verify port availability.

### 6. Project Structure Disorganization

**Problem**: Files were scattered across the codebase without clear organization.

**Solution**:
- Reorganized project into dedicated directories for tools, tests, docs, and examples.
- Updated path references in scripts to account for the new structure.
- Created verification mechanisms to ensure the reorganization didn't break functionality.
- Documented the new structure in maintenance guides.

## Future Enhancement Areas

### 1. More Robust Variable Dependency Tracking
- Track dependencies at the individual variable level rather than step level.
- Implement a directed acyclic graph (DAG) for visualizing variable dependencies.

### 2. Enhanced Concurrency Model
- Replace the simple threading model with asyncio for better performance.
- Implement resource throttling for high-concurrency environments.

### 3. Extended Error Recovery
- Add more sophisticated error recovery mechanisms.
- Implement automatic workflow repair for common issues.

### 4. Visualization Improvements
- Enhance the debugging UI with real-time workflow visualization.
- Add graphical representation of variable dependencies.

### 5. Testing Infrastructure
- Implement comprehensive unit and integration tests.
- Create synthetic workflow testing tools for performance assessment.