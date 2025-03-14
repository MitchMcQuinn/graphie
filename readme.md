# Graphie - A Neo4j-Powered Conversational Workflow Engine with Synchronized Variable Handling

Graphie is a flexible, graph-based conversational workflow engine that uses Neo4j to define and manage interactive chat flows. It enables building structured conversations with AI assistance and human-in-the-loop interactions, with advanced support for parallel workflows and synchronized variable handling.

## Overview

Graphie provides a framework where conversational workflows are defined as graph structures in Neo4j. Each step in a conversation is represented by a node, with directional relationships defining the flow between steps. The system features:

- **Graph-driven workflows:** Define complex conversational flows through Neo4j graph structures
- **Stateful context management:** Maintain conversation context across multiple interactions
- **Parallel workflow paths:** Process multiple workflow branches simultaneously
- **Synchronized variable handling:** Auto-defer steps until required variables become available
- **OpenAI integration:** Generate AI responses through seamless OpenAI API integration
- **Human-in-the-loop design:** Interactively gather user input at defined points in workflows
- **Variable passing:** Reference outputs from previous steps in subsequent actions
- **Default values:** Provide fallback values for variable references, enabling more resilient workflows
- **Looping workflows:** Create iterative conversation patterns with cyclic graph structures
- **Conditional branching:** Create dynamic conversations with branching logic
- **Real-time debugging:** Monitor workflow execution and variable states

## System Architecture

### Core Components

1. **Web Interface (Flask)**: Manages the user interface and API endpoints
2. **Synced Workflow Engine**: Processes workflow steps with intelligent variable synchronization
3. **Neo4j Database**: Stores the workflow definitions using a graph structure
4. **Utility Modules**: Provides functionality for generating responses, analyzing input, and replying to users

### Engine Evolution

Graphie has evolved through several engine implementations:

1. **Original Engine (engine.py)**: Basic workflow processing
2. **Fixed Engine (fixed_engine.py)**: Added support for parallel path processing
3. **Synced Engine (engine.py)**: Enhanced with variable synchronization and deferred processing

The current implementation is the Synced Engine, which builds on top of the fixed engine but adds improved variable handling.

### Workflow Ontology

The workflow system uses the following Neo4j structure:

#### STEP Nodes
Each step in a workflow is represented by a node with properties:
- `id`: Unique identifier for referencing the step
- `description`: Human-readable description of the step's purpose
- `function`: Action to execute (e.g., `analyze.analyze_input`, `request.request`, `fixed_reply.fixed_reply`)
- `input`: JSON-formatted parameters for the function

#### NEXT Relationships
Connections between steps with properties:
- `id`: Unique identifier for the relationship
- `description`: Description of the transition's purpose
- `function`: Optional conditional function that determines if this path should be taken
- `input`: Parameters for the condition function

## Synced Workflow Engine Features

### Key Features

1. **Indefinite Variable Readiness Checks**: The engine will keep trying to resolve variables as long as the session is active, rather than giving up after a few attempts.

2. **Deferred Step Processing**: Steps that reference unavailable variables are automatically deferred and retried later, allowing the workflow to continue with other paths.

3. **Non-Blocking Architecture**: Uses threading to manage retries without blocking the main execution path, ensuring responsive UI.

4. **Enhanced Debugging**: Provides additional endpoints to monitor variable availability and deferred steps.

5. **Session Management**: Properly tracks whether a session is active to avoid unnecessary processing.

### How It Works

#### Variable Resolution Process

1. When a workflow step is processed, the engine first checks if all required variables are available.
2. If variables are missing, the step is marked as "deferred" and queued for later processing.
3. A background thread is scheduled to retry the step after a delay.
4. The retry process continues indefinitely as long as the session remains active.
5. Once all variables become available, the deferred step is processed, and the workflow continues.

#### Example Scenario

Consider a workflow with parallel paths:
- Path A: Analyzes sentiment (slow operation)
- Path B: Extracts entities (fast operation)
- Path C: Summarizes both results (depends on A and B)

With the synced engine:
1. Paths A and B start executing in parallel
2. Path B completes quickly and updates the session with entity data
3. Path C tries to execute but needs data from Path A, so it's deferred
4. Path A eventually completes and updates the session with sentiment data
5. The deferred Path C is automatically retried, finds all variables available, and completes successfully

## Usage

### Running the Application

```bash
# Make the setup script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

### Debugging Endpoints

- `/debug_workflow`: Overview of workflow state, paths, and deferred steps
- `/debug_variables`: Detailed view of variable availability and what deferred steps are waiting for
- `/stream_log`: Real-time streaming of log events for debugging

## Implementation Details

The implementation consists of:

1. **engine.py**: The main workflow engine with variable synchronization
2. **app.py**: Flask application using the engine
3. **setup.sh**: Script to set up and run the implementation
4. **Utils modules**: Modules for analysis, request handling, and fixed replies

### Key Methods

- `_replace_variables`: Detects missing variables and returns None to trigger deferral
- `_process_step`: Handles variable resolution failures by deferring steps
- `_retry_deferred_step`: Manages the retry process for deferred steps
- `mark_session_inactive`: Stops retrying when a session ends

## Limitations

1. The current implementation uses a simple thread-based approach for retries, which may not be optimal for very high-concurrency systems.

2. There's no maximum lifetime for deferred steps, which could potentially lead to resource issues in long-running sessions.

3. Variable dependencies are only tracked at the step level, not at the individual variable level, which may lead to unnecessary retries.

## Complete Workflow Example

Here's a complete example of a looping Q&A workflow defined in Neo4j that demonstrates variable references with default values:

```cypher
// Create the root node (entry point)
CREATE (root:STEP {
  id: "root",
  description: "Starting point for the Q&A workflow",
  function: "reply.reply",
  input: '{"reply": "Welcome to the Q&A Assistant! I can help answer your questions."}'
})

// Create a node to get the user's question
CREATE (get_question:STEP {
  id: "get-question",
  description: "Ask the user what they want to know",
  function: "request.request",
  input: '{"statement": "What would you like to know about?"}'
})

// Create a node to generate an answer
CREATE (generate_answer:STEP {
  id: "generate-answer",
  description: "Generate an answer using OpenAI",
  function: "generate.generate",
  input: '{"system": "You are a helpful assistant that provides accurate, concise answers.", "user": "@{get-question}.response", "temperature": "0.7"}'
})

// Create a node to provide the answer
CREATE (provide_answer:STEP {
  id: "provide-answer",
  description: "Send the generated answer to the user",
  function: "reply.reply",
  input: '{"reply": "@{generate-answer}.generation"}'
})

// Create a node to ask if user has more questions
CREATE (more_questions:STEP {
  id: "more-questions",
  description: "Ask if the user has more questions",
  function: "request.request",
  input: '{"statement": "Do you have any more questions? (yes/no)"}'
})

// Create a node to store conversation history
CREATE (conversation_history:STEP {
  id: "conversation-history",
  description: "Store the conversation history for context",
  function: "store.append",
  input: '{"key": "history", "value": {"question": "@{get-question}.response", "answer": "@{generate-answer}.generation"}, "initial": "@{conversation-history}.history|[]"}'
})

// Connect the steps with NEXT relationships
CREATE 
  (root)-[:NEXT {id: "to-question"}]->(get_question),
  (get_question)-[:NEXT {id: "to-generate"}]->(generate_answer),
  (generate_answer)-[:NEXT {id: "to-provide"}]->(provide_answer),
  (provide_answer)-[:NEXT {id: "to-history"}]->(conversation_history),
  (conversation_history)-[:NEXT {id: "to-more"}]->(more_questions),
  // Conditional branch for additional questions - CREATES A LOOP
  (more_questions)-[:NEXT {
    id: "if-yes",
    description: "If the user wants more questions",
    function: "condition.equals",
    input: '{"value": "@{more-questions}.response", "equals": "yes"}'
  }]->(get_question),
  // End workflow if no more questions
  (more_questions)-[:NEXT {
    id: "if-no",
    description: "If the user doesn't want more questions",
    function: "condition.not_equals",
    input: '{"value": "@{more-questions}.response", "equals": "yes"}'
  }]->(end:STEP {
    id: "end",
    description: "End of workflow",
    function: "reply.reply",
    input: '{"reply": "Thank you for using our Q&A Assistant. Here\'s a summary of our conversation: @{conversation-history}.history"}'
  })
```

## Running the Application

### Prerequisites
- Python 3.8+
- Neo4j database
- OpenAI API key

### Environment Setup
Create a `.env.local` file with the following variables:
```
# OpenAI API key
OPENAI_API_KEY=your_openai_api_key

# Neo4j Aura connection details
NEO4J_URL=your_neo4j_url
NEO4J_USERNAME=your_neo4j_username  
NEO4J_PASSWORD=your_neo4j_password

# Flask secret key
FLASK_SECRET_KEY=your_secret_key
```

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up the Neo4j database with your workflow

### Starting the Application
Run the setup script:
```
./setup.sh
```
The web interface will be available at http://localhost:5001

## Extending Functionality

### Adding Custom Functions
You can extend Graphie by creating new utility functions:

1. Create a new Python file in the `utils` directory
2. Define functions that take `session` and `input_data` parameters
3. Store results in the session for later reference
4. Reference the new function in your Neo4j workflow nodes

### Creating Conditional Branches
Design complex workflows with conditional logic:

1. Define multiple NEXT relationships from a single node
2. Add condition functions to relationships to control the flow
3. Set appropriate input data for condition evaluation

### Implementing Looping Workflows
Create iterative conversation patterns using cyclic graph structures:

1. Add a NEXT relationship that points back to an earlier step in the workflow
2. Use the default value syntax (`@{node-id}.key|default_value`) for variables that need initialization
3. Implement a condition function to determine when to continue or exit the loop
4. Consider using a storage step to accumulate data across iterations (like the `conversation-history` example)
5. Be mindful of infinite loops - always ensure there's a clear exit condition

For example, to create a loop that collects multiple items:
```cypher
CREATE (collect_items:STEP {
  id: "collect-items",
  description: "Collect an item from the user",
  function: "request.request",
  input: '{"statement": "Enter an item (or type \"done\" to finish):"}'
})

CREATE (store_item:STEP {
  id: "store-item",
  description: "Add the item to our collection",
  function: "store.append",
  input: '{"key": "items", "value": "@{collect-items}.response", "initial": "@{store-item}.items|[]"}'
})

CREATE (check_done:STEP {
  id: "check-done",
  description: "Check if the user is done entering items",
  function: "condition.equals",
  input: '{"value": "@{collect-items}.response", "equals": "done"}'
})

// Connect steps with looping structure
CREATE
  (collect_items)-[:NEXT]->(store_item),
  // Loop back if not done
  (store_item)-[:NEXT {
    function: "condition.not_equals",
    input: '{"value": "@{collect-items}.response", "equals": "done"}'
  }]->(collect_items),
  // Exit loop when done
  (store_item)-[:NEXT {
    function: "condition.equals",
    input: '{"value": "@{collect-items}.response", "equals": "done"}'
  }]->(summary:STEP {
    id: "summary",
    description: "Summarize collected items",
    function: "reply.reply",
    input: '{"reply": "Here are all the items you entered: @{store-item}.items"}'
  })
```

This pattern can be adapted for various use cases such as:
- Multi-turn information gathering
- Iterative refinement of responses
- Continuous question-answering until user satisfaction is reached
- Building lists or collections incrementally

## Troubleshooting

### Common Issues
- **Neo4j Connection Errors**: Check your Neo4j credentials and ensure the database is running
- **Missing Variables**: Verify that referenced variables exist in the session data
- **Workflow Not Progressing**: Check the logs for errors in function execution or condition evaluation
- **Infinite Loops**: If your workflow seems stuck in a loop, verify your condition functions have proper exit conditions
- **Default Value Issues**: Make sure default values use the correct syntax `@{node-id}.key|default_value` with no spaces around the pipe character
- **Variable Reference Errors**: When using self-referential variables in loops (like `@{step-id}.key|[]`), check that the variable name exactly matches the node ID

### Debugging
Use the built-in logging system to troubleshoot issues:
- Check console output for detailed logs
- Monitor the session data to track variable state
- Inspect the workflow structure in Neo4j to verify correctness
- For loops, examine the workflow visualization to ensure the loop path connects correctly back to the intended step

## Additional Resources
- [Neo4j Documentation](https://neo4j.com/docs/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Project Structure

The project uses the following structure:

- **Core Application:**
  - **app.py**: Main Flask application
  - **engine.py**: Synced workflow engine with variable synchronization
  - **fixed_engine.py**: Foundation engine that is extended by the synced engine
  - **setup.sh**: Main script to set up and start the application

- **Utilities:**
  - **utils/**: Utility modules (analyze, request, fixed_reply, etc.)
  - **tools/**: Scripts for managing and updating the workflow

- **Documentation:**
  - **docs/**: Documentation files including maintenance guide
  - **examples/**: Example workflow definitions in Cypher

- **Testing:**
  - **tests/**: Test and debugging scripts

- **Web Interface:**
  - **templates/**: HTML templates
  - **static/**: Static assets (CSS, JS, etc.)

- **Other:**
  - **obsolete_files/**: Archived old versions (for reference)
