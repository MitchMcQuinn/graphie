# Graphie - A Neo4j-Powered Conversational Workflow Engine

Graphie is a flexible, graph-based conversational workflow engine that uses Neo4j to define and manage interactive chat flows. It enables building structured conversations with AI assistance and human-in-the-loop interactions.

## Overview

Graphie provides a framework where conversational workflows are defined as graph structures in Neo4j. Each step in a conversation is represented by a node, with directional relationships defining the flow between steps. The system features:

- **Graph-driven workflows:** Define complex conversational flows through Neo4j graph structures
- **Stateful context management:** Maintain conversation context across multiple interactions
- **OpenAI integration:** Generate AI responses through seamless OpenAI API integration
- **Human-in-the-loop design:** Interactively gather user input at defined points in workflows
- **Variable passing:** Reference outputs from previous steps in subsequent actions
- **Conditional branching:** Create dynamic conversations with branching logic

## System Architecture

### Core Components

1. **Web Interface (Flask)**: Manages the user interface and API endpoints
2. **Workflow Engine**: Processes workflow steps and handles the conversation flow logic
3. **Neo4j Database**: Stores the workflow definitions using a graph structure
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

- **Syntax**: `@{node_id}.key` 
- **Example**: `@{get-question}.response` references the user's response from a step with ID `get-question`
- **Implementation**: Variables are processed by the workflow engine, which replaces references with actual values before executing functions

## Complete Workflow Example

Here's a complete example of a Q&A workflow defined in Neo4j:

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

// Connect the steps with NEXT relationships
CREATE 
  (root)-[:NEXT {id: "to-question"}]->(get_question),
  (get_question)-[:NEXT {id: "to-generate"}]->(generate_answer),
  (generate_answer)-[:NEXT {id: "to-provide"}]->(provide_answer),
  (provide_answer)-[:NEXT {id: "to-more"}]->(more_questions),
  // Conditional branch for additional questions
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
    input: '{"reply": "Thank you for using our Q&A Assistant. Have a great day!"}'
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

## Troubleshooting

### Common Issues
- **Neo4j Connection Errors**: Check your Neo4j credentials and ensure the database is running
- **Missing Variables**: Verify that referenced variables exist in the session data
- **Workflow Not Progressing**: Check the logs for errors in function execution or condition evaluation

### Debugging
Use the built-in logging system to troubleshoot issues:
- Check console output for detailed logs
- Monitor the session data to track variable state
- Inspect the workflow structure in Neo4j to verify correctness

## Additional Resources
- [Neo4j Documentation](https://neo4j.com/docs/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Flask Documentation](https://flask.palletsprojects.com/)
