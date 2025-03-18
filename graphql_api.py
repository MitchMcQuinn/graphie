"""
graphql_api.py
--------------
This module implements the GraphQL API for the workflow engine using Ariadne.

Purpose:
    Provides a GraphQL endpoint for frontend clients to interact with the workflow engine.
"""

import json
import logging
from ariadne import ObjectType, QueryType, MutationType, ScalarType, make_executable_schema
from ariadne.asgi import GraphQL
from graph_engine import get_graph_workflow_engine
from utils.session_manager import get_session_manager
from utils.database import get_neo4j_driver

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize type definitions
query = QueryType()
mutation = MutationType()
frontend_state = ObjectType("FrontendState")
workflow_result = ObjectType("WorkflowResult")
chat_message = ObjectType("ChatMessage")
session_status = ObjectType("SessionStatus")
json_scalar = ScalarType("JSON")

# Define JSON scalar
@json_scalar.serializer
def serialize_json(value):
    """Serialize JSON values"""
    return value

@json_scalar.value_parser
def parse_json_value(value):
    """Parse JSON values"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value

# Query resolvers
@query.field("frontendState")
def resolve_frontend_state(_, info, sessionId):
    """Get frontend state for a session"""
    engine = get_graph_workflow_engine()
    return engine.get_frontend_state(sessionId)

@query.field("chatHistory")
def resolve_chat_history(_, info, sessionId):
    """Get chat history for a session"""
    engine = get_graph_workflow_engine()
    return engine.get_chat_history(sessionId)

@query.field("hasSession")
def resolve_has_session(_, info, sessionId):
    """Check if a session exists"""
    engine = get_graph_workflow_engine()
    return engine.has_session(sessionId)

@query.field("sessionStatus")
def resolve_session_status(_, info, sessionId):
    """Get session status"""
    engine = get_graph_workflow_engine()
    status = engine.get_session_status(sessionId)
    
    # Transform the status object to match the schema
    result = {
        "status": status.get("status", "unknown"),
        "nextSteps": status.get("next_steps", []),
        "hasError": "error" in status,
        "errorMessage": status.get("error") if "error" in status else None,
        "hasChatHistory": bool(status.get("chat_history", []))
    }
    
    return result

# Mutation resolvers
@mutation.field("startWorkflow")
def resolve_start_workflow(_, info, sessionId=None):
    """Start a new workflow"""
    engine = get_graph_workflow_engine()
    result = engine.start_workflow(sessionId)
    
    # Format the result for the schema
    frontend_state = engine.get_frontend_state(sessionId if sessionId else result.get("session_id", ""))
    
    return {
        "frontendState": frontend_state,
        "success": "error" not in result if result else False,
        "errorMessage": result.get("error") if result and "error" in result else None,
        "hasMoreSteps": result.get("has_more_steps", False) if result else False,
        "status": result.get("status", "unknown") if result else "error"
    }

@mutation.field("sendMessage")
def resolve_send_message(_, info, sessionId, message):
    """Send a message to the workflow"""
    engine = get_graph_workflow_engine()
    result = engine.continue_workflow(message, sessionId)
    
    # Format the result for the schema
    frontend_state = engine.get_frontend_state(sessionId)
    
    return {
        "frontendState": frontend_state,
        "success": "error" not in result,
        "errorMessage": result.get("error") if "error" in result else None,
        "hasMoreSteps": result.get("has_more_steps", False),
        "status": result.get("status", "unknown")
    }

@mutation.field("continueProcessing")
def resolve_continue_processing(_, info, sessionId):
    """Continue processing workflow steps"""
    engine = get_graph_workflow_engine()
    result = engine.process_workflow_steps(sessionId)
    
    # Format the result for the schema
    frontend_state = engine.get_frontend_state(sessionId)
    
    return {
        "frontendState": frontend_state,
        "success": "error" not in result,
        "errorMessage": result.get("error") if "error" in result else None,
        "hasMoreSteps": result.get("has_more_steps", False),
        "status": result.get("status", "unknown")
    }

# Load the schema
with open("schema.graphql") as schema_file:
    type_defs = schema_file.read()

# Make the executable schema
schema = make_executable_schema(
    type_defs, 
    query, 
    mutation, 
    frontend_state, 
    workflow_result, 
    chat_message, 
    session_status,
    json_scalar
)

# Create the GraphQL application
graphql_app = GraphQL(schema, debug=True)

# Function to add the GraphQL app to a Flask app
def add_graphql_route(app, path="/graphql"):
    """
    Add the GraphQL route to a Flask app
    
    Args:
        app: The Flask application
        path: The URL path for the GraphQL endpoint
        
    Returns:
        None
    """
    from flask import request, jsonify
    
    @app.route(path, methods=["GET", "POST"])
    def graphql_handler():
        """Handle GraphQL requests"""
        # GET requests are typically for GraphiQL UI
        if request.method == "GET":
            return jsonify({"message": "GraphQL endpoint active. Use POST for queries."})
        
        # POST requests contain the GraphQL query
        data = request.json
        
        if not data:
            return jsonify({"errors": [{"message": "No JSON data provided"}]}), 400
        
        # Extract the query, variables, and operation_name
        query = data.get("query")
        variables = data.get("variables")
        operation_name = data.get("operationName")
        
        if not query:
            return jsonify({"errors": [{"message": "No GraphQL query provided"}]}), 400
        
        # Execute the query
        result = schema.execute(
            query,
            variable_values=variables,
            context_value={"request": request},
            operation_name=operation_name
        )
        
        # Return the result
        return jsonify(result.to_dict()) 