# Graphie - A Neo4j-Powered Conversational Workflow Engine

Graphie is a flexible, graph-based conversational workflow engine that uses Neo4j to define and manage interactive chat flows. It enables building structured conversations with AI assistance and human-in-the-loop interactions.

## Overview

Graphie provides a framework where conversational workflows are defined as graph structures in Neo4j. Each step in a conversation is represented by a node, with directional relationships defining the flow between steps. The system features:

- **Graph-driven workflows:** Define complex conversational flows through Neo4j graph structures
- **Stateful context management:** Maintain conversation context across multiple interactions
- **OpenAI integration:** Generate AI responses through seamless OpenAI API integration
- **Human-in-the-loop design:** Interactively gather user input at defined points in workflows
- **Variable passing:** Reference outputs from previous steps in subsequent actions
- **Default values:** Provide fallback values for variable references, enabling more resilient workflows
- **Looping workflows:** Create iterative conversation patterns with cyclic graph structures
- **Conditional branching:** Create dynamic conversations with branching logic

## System Architecture

### Core Components

1. **Web Interface (Flask)**: Manages the user interface and API endpoints
2. **Workflow Engine**: Processes workflow steps and handles the conversation flow logic
3. **Neo4j Database**: Stores the workflow definitions using a graph structure and additional memory for the agent to reference on-demand
4. **Utility Modules**: Provides functionality for generating responses, requesting user input, and replying to users

### Workflow Ontology

The workflow system uses the following Neo4j structure:

#### STEP Nodes
Each step in a workflow is represented by a node with properties:
- `id`: Unique identifier for referencing the step
- `description`: Human-readable description of the step's purpose
- `function`: Action to execute (e.g., `generate.generate`, `request.request`, `reply.reply`)
- `input`: JSON-formatted parameters for the function

#### NEXT Relationships
Connections between steps with properties:
- `id`: Unique identifier for the relationship
- `description`: Description of the transition's purpose
- `function`: Optional conditional function that determines if this path should be taken
- `input`: Parameters for the condition function

### Core Utilities

Graphie includes three primary utility modules:

#### 1. `generate.py`
Integrates with OpenAI to generate AI responses:
```python
# Example usage in workflow
{
  "function": "generate.generate",
  "input": {
    "system": "You are a helpful assistant skilled in answering questions about Neo4j.",
    "user": "@{get-question}.response",
    "temperature": "0.7",
    "model": "gpt-4-turbo"
  }
}
```

#### 2. `request.py`
Manages human-in-the-loop interactions by pausing the workflow and awaiting user input:
```python
# Example usage in workflow
{
  "function": "request.request",
  "input": {
    "statement": "What would you like to know about graph databases?"
  }
}
```

#### 3. `reply.py`
Sends responses to the user interface:
```python
# Example usage in workflow
{
  "function": "reply.reply",
  "input": {
    "reply": "Here's the information you requested: @{generate-answer}.generation"
  }
}
```

## Variable Reference System

Graphie includes a powerful variable reference system to pass data between workflow steps:

- **Basic Syntax**: `@{node_id}.key` 
- **Example**: `@{get-question}.response` references the user's response from a step with ID `get-question`
- **Default Values**: `@{node_id}.key|default_value` - If the referenced variable doesn't exist, the default value is used
- **Example with Default**: `@{user-input}.response|"No input provided"` - Uses "No input provided" if the response is missing
- **Implementation**: Variables are processed by the workflow engine, which replaces references with actual values before executing functions

The default value capability is particularly useful for:
- Creating resilient workflows that can handle missing or incomplete data
- Enabling looping workflows by providing initial values for variables that will be populated in later iterations
- Establishing fallback content for optional user inputs

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

This workflow demonstrates several key features:
1. **Looping capability**: The workflow can loop back from `more_questions` to `get_question` when the user wants to continue
2. **Default value usage**: The `conversation-history` step uses `@{conversation-history}.history|[]` to initialize with an empty array on first execution
3. **Stateful context**: The conversation history accumulates across multiple iterations of the loop
4. **Conditional branching**: Different paths are taken based on the user's response to continue or end the workflow

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
Run the Flask application:
```
python app.py
```
The web interface will be available at http://localhost:5000

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
