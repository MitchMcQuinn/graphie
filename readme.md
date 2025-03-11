# Graphie (A Neo4j enabled chatbot)
Graphie is a chatbot that's been enabled with a workflow management system using a graph database. 

## Overview
The chat session follows a structured process outlined via STEP nodes and NEXT relationships in the graph, starting on the node with the id that equals "root". Each action node represents a function (located in the "utils" folder) that must be run before proceeding to the next step. Each action accepts a function value (module.function), and a json object string value that holds any of the values the action needs to operate. Importantly, each function should make sure that its responses temporarily are stored in the working session so they can be referenced in later inputs (see the variable handling system below). These utilities can be extended in the future, but for now we should focus on the three most essential:
- generate.py
This function accepts these values as input: system, agent, user, temperature, model
It then connects with OpenAI to generate a textual output

- request.py
This is the "human in the loop" function. It asks the user a question or query and awaits a response, then stores that response for later input. It accepts a "statement" variable as input which is uses to query the user (ie. "What can I help you with?"). It's important to note that the workflow will pause until a response is received.

- reply.py
This action simply forwards a response to the user in the chat window. It accepts a "reply" variable which is forwards to the user. 

## Features

* Graph-based workflow engine for flexible conversation flows
* Integration with Neo4j database
* OpenAI API for natural language generation
* Dynamic function loading for extensibility
* Stateful conversations with context tracking

## Dynamic Workflow Ontology
The workflow system uses the following Neo4j structure:

### STEP Nodes
Represent individual steps in a workflow:

id: [unique identifier for the node, required for variable handling]
description: [a short description of the node's purpose]
function: [function_name] - Python function to execute
input: [array of key:value pairs] - Parameters for the function

### NEXT Relationships
Connect steps in a workflow:

id: [unique identifier for the relationship, require for variable handling]
description: [a short description of the relationship's purpose]
function: [function_name] - Condition function (returns boolean)
input: [array of key:value pairs] - Parameters for the condition

## Variable Handling
State is maintained across steps using variable references:

@{node/relationship id}.{key} - Accesses output from previous steps
Example Workflow
A simple Q&A workflow might be defined as:

Start Node (id: "root") - Entry point for the workflow
No function defined (triggered by "@qa-bot" mention)
Request Node (id: "get-question")

-next->

function: "request.request"
input: {"query": "What would you like to know about?"}
Generate Node (id: "generate-answer")

-next->

function: "generate.generate"
input: {"system": "You are a helpful assistant", "user": "@{get-question}.response", "temperature": "0.5"}
Respond Node (id: "provide-answer")

-next->

function: "respond"
input: {"response": "@{generate-answer}.generation"}

# Environment variables
These enviroment variables already exist inside the .env.local
## OpenAI API key
OPENAI_API_KEY

## Neo4j Aura connection details
NEO4J_URL
NEO4J_USERNAME
NEO4J_PASSWORD

## Flask secret key
FLASK_SECRET_KEY
