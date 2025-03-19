#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
import pprint

# Load environment variables
load_dotenv('../.env.local')  # Try relative path first
if not os.path.exists('../.env.local'):
    load_dotenv('.env.local')  # Try current directory

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
    print("Error: Neo4j connection details are missing.")
    print("Please ensure NEO4J_URL, NEO4J_USERNAME, and NEO4J_PASSWORD are set in .env.local")
    exit(1)

class WorkflowViewer:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def view_all_nodes(self):
        """View all STEP nodes in the workflow"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:STEP)
                RETURN n
                ORDER BY n.id
                """
            )
            
            print("\n=== All STEP Nodes ===")
            nodes = []
            for record in result:
                node = dict(record['n'])
                nodes.append(node)
                
            # Pretty print the nodes
            pprint.pprint(nodes, indent=2)
            
            return nodes
    
    def view_node_connections(self):
        """View all NEXT relationships in the workflow"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (source:STEP)-[r:NEXT]->(target:STEP)
                RETURN source.id as source_id, 
                       target.id as target_id, 
                       properties(r) as relationship_props
                ORDER BY source.id, target.id
                """
            )
            
            print("\n=== Node Connections (NEXT relationships) ===")
            connections = []
            for record in result:
                connection = {
                    'source': record['source_id'],
                    'target': record['target_id'],
                    'properties': record['relationship_props']
                }
                connections.append(connection)
                
            # Pretty print the connections
            pprint.pprint(connections, indent=2)
            
            return connections
    
    def view_complete_workflow(self):
        """View the complete workflow structure"""
        with self.driver.session() as session:
            # First, get all the nodes
            result = session.run(
                """
                MATCH (n:STEP)
                RETURN collect(n) as nodes
                """
            )
            
            record = result.single()
            nodes = {dict(node)['id']: dict(node) for node in record['nodes']}
            
            # Then, get all relationships
            result = session.run(
                """
                MATCH (source:STEP)-[r:NEXT]->(target:STEP)
                RETURN collect({
                    source: source.id,
                    target: target.id,
                    relationship: properties(r)
                }) as relationships
                """
            )
            
            record = result.single()
            relationships = record['relationships']
            
            # Build a workflow representation
            workflow = {
                'nodes': nodes,
                'relationships': relationships
            }
            
            print("\n=== Complete Workflow Structure ===")
            print(f"Total nodes: {len(nodes)}")
            print(f"Total relationships: {len(relationships)}")
            
            # Generate a text representation of the workflow
            print("\nWorkflow Visualization:")
            self._visualize_workflow(workflow)
            
            return workflow
    
    def _visualize_workflow(self, workflow):
        """Create a simple text visualization of the workflow"""
        # Find the root node
        root_id = None
        for node_id, node in workflow['nodes'].items():
            if node_id == 'root':
                root_id = node_id
                break
        
        if not root_id:
            print("No root node found!")
            return
        
        # Build an adjacency list
        adjacency = {}
        for rel in workflow['relationships']:
            source = rel['source']
            target = rel['target']
            
            if source not in adjacency:
                adjacency[source] = []
            
            adjacency[source].append({
                'target': target,
                'properties': rel['relationship']
            })
        
        # Perform a DFS from the root
        visited = set()
        
        def dfs(node_id, depth=0):
            if node_id in visited:
                print("  " * depth + f"└─ {node_id} (already visited)")
                return
            
            visited.add(node_id)
            node = workflow['nodes'][node_id]
            
            indent = "  " * depth
            print(f"{indent}└─ {node_id} [STEP]")
            
            # Print node properties
            for key, value in node.items():
                if key != 'id':
                    print(f"{indent}   ├─ {key}: {value}")
            
            # Print outgoing relationships
            if node_id in adjacency:
                for idx, edge in enumerate(adjacency[node_id]):
                    target = edge['target']
                    properties = edge['properties']
                    
                    print(f"{indent}   └─ NEXT → {target}")
                    
                    # Print relationship properties
                    if properties:
                        for key, value in properties.items():
                            print(f"{indent}      ├─ {key}: {value}")
                    
                    # Recurse
                    dfs(target, depth + 3)
        
        # Start DFS from root
        dfs(root_id)

if __name__ == "__main__":
    print("=== Neo4j Workflow Viewer ===")
    print(f"Connecting to: {NEO4J_URL}")
    
    viewer = WorkflowViewer()
    try:
        # View all nodes
        viewer.view_all_nodes()
        
        # View all connections
        viewer.view_node_connections()
        
        # View the complete workflow
        viewer.view_complete_workflow()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        viewer.close()
