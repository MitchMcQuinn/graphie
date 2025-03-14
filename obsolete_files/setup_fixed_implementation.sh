#!/bin/bash

# Set up logging
echo "Setting up fixed implementation for parallel workflow..."

# Check for Neo4j environment variables
if [ ! -f .env.local ]; then
    echo "Error: .env.local file not found."
    echo "Please create this file with your Neo4j credentials:"
    echo "NEO4J_URL=bolt://localhost:7687"
    echo "NEO4J_USERNAME=neo4j"
    echo "NEO4J_PASSWORD=your_password"
    echo "OPENAI_API_KEY=your_openai_api_key"
    exit 1
fi

# Update the Neo4j database with our workflow
echo "Updating Neo4j database with fixed workflow..."
python update_workflow_for_fixed_engine.py

if [ $? -ne 0 ]; then
    echo "Error: Failed to update Neo4j database."
    echo "Please check your Neo4j connection and credentials."
    exit 1
fi

echo "Neo4j database updated successfully."

# Clean up the workflow to ensure all nodes are using the right functions
echo "Cleaning up workflow to fix any issues..."
python check_and_clean_workflow.py

if [ $? -ne 0 ]; then
    echo "Warning: Workflow cleanup encountered issues."
    echo "Check the logs for details, but continuing with verification."
fi

# Fix variable handling in the show-analysis node
echo "Fixing variable handling in analysis nodes..."
python fix_show_analysis_node.py

if [ $? -ne 0 ]; then
    echo "Warning: Failed to fix analysis nodes."
    echo "Check the logs for details, but continuing with verification."
fi

# Check the workflow configuration
echo "Verifying workflow configuration..."
python check_workflow_steps.py

if [ $? -ne 0 ]; then
    echo "Warning: Workflow verification encountered issues."
    echo "Check the logs for details, but continuing with application startup."
fi

# Start the fixed application
echo "Starting fixed application on port 5001..."
echo "Note: Make sure the original application is not running on port 5000 to avoid confusion."
python app_fixed.py

# If we get here, all is well
echo "Fixed implementation setup completed." 