"""
check_workflow_update_status.py
----------------------------
This script checks which workflow nodes have been updated for the new
session management system and which ones still need updating.
"""

import logging
from tabulate import tabulate
from engine import get_neo4j_driver

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_update_status():
    """Check which workflow nodes have been updated for the new session management system"""
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Failed to connect to Neo4j")
        return
    
    try:
        with driver.session() as session:
            # Get all STEP nodes
            result = session.run("""
                MATCH (s:STEP)
                WHERE s.input IS NOT NULL
                RETURN s.id as id, 
                       s.function as function,
                       s.input as input,
                       s.updated_for_session_nodes as updated,
                       s.original_input IS NOT NULL as has_original
            """)
            
            nodes = [dict(record) for record in result]
            
            # Process the data
            updated_nodes = []
            pending_nodes = []
            
            for node in nodes:
                node_id = node['id']
                function = node['function']
                input_str = node['input']
                is_updated = node.get('updated', False)
                has_original = node.get('has_original', False)
                
                # Check if this node has variable references
                has_variables = '@{' in input_str
                
                if is_updated and has_original:
                    updated_nodes.append({
                        'id': node_id,
                        'function': function,
                        'has_variables': has_variables
                    })
                elif has_variables:
                    pending_nodes.append({
                        'id': node_id,
                        'function': function,
                        'input': input_str[:50] + ('...' if len(input_str) > 50 else '')
                    })
            
            # Print the results
            print("\n=== Workflow Update Status ===")
            print(f"Total nodes with input: {len(nodes)}")
            print(f"Nodes with variable references: {len([n for n in nodes if '@{' in n['input']])}")
            print(f"Updated nodes: {len(updated_nodes)}")
            print(f"Pending nodes: {len(pending_nodes)}")
            
            if updated_nodes:
                print("\n=== Updated Nodes ===")
                headers = ['ID', 'Function', 'Has Variables']
                table = [[n['id'], n['function'], n['has_variables']] for n in updated_nodes]
                print(tabulate(table, headers=headers, tablefmt='grid'))
            
            if pending_nodes:
                print("\n=== Pending Nodes ===")
                headers = ['ID', 'Function', 'Input Preview']
                table = [[n['id'], n['function'], n['input']] for n in pending_nodes]
                print(tabulate(table, headers=headers, tablefmt='grid'))
            
            # Get count of variable references by type
            variable_counts = {}
            for node in nodes:
                input_str = node['input']
                if '@{' in input_str:
                    # Extract variable references using a simple approach
                    parts = input_str.split('@{')
                    for part in parts[1:]:  # Skip the first part (before any @{)
                        if '}' in part:
                            var_name = part.split('}')[0]
                            variable_counts[var_name] = variable_counts.get(var_name, 0) + 1
            
            if variable_counts:
                print("\n=== Variable References ===")
                headers = ['Variable', 'Count']
                table = [[var, count] for var, count in sorted(variable_counts.items(), key=lambda x: -x[1])]
                print(tabulate(table, headers=headers, tablefmt='grid'))
            
            return {
                'total_nodes': len(nodes),
                'nodes_with_variables': len([n for n in nodes if '@{' in n['input']]),
                'updated_nodes': len(updated_nodes),
                'pending_nodes': len(pending_nodes),
                'variable_counts': variable_counts
            }
    
    except Exception as e:
        logger.error(f"Error checking update status: {str(e)}")
        return None

if __name__ == "__main__":
    print("Checking workflow update status...")
    results = check_update_status()
    
    if results:
        # Print a summary report
        print("\n=== Summary ===")
        print(f"Progress: {results['updated_nodes']}/{results['nodes_with_variables']} nodes updated " +
              f"({results['updated_nodes']/max(1, results['nodes_with_variables'])*100:.1f}%)")
        print(f"Remaining: {results['pending_nodes']} nodes need updating")
        
        # If all nodes are updated, print a success message
        if results['pending_nodes'] == 0 and results['updated_nodes'] > 0:
            print("\n✅ All workflow nodes have been updated successfully!")
        else:
            print("\n⚠️ Some workflow nodes still need to be updated.")
            print("Run the update_workflow.py script to complete the updates.")
    
    print("Done!") 