// development notes
Features to implement:
# Dependencies / Parallel processing
Forward NEXT relationships are followed optimistically. They are followed under all conditions unless their function returns 'false'.
Before execution, STEP nodes must wait for all WAIT relationships (dependencies)

# nested flows
Other 'root' nodes that can be run in steps like API calls. 
Define the required inputs for a flow in the root node. 
Reduces repetition in the graph of common patterns of behavior.

# Markdown formatting and streaming responses

# Template nodes?
Nodes that serve preformatted property values as defaults to other nodes.

# cypher implementation
A type of generation that 



# Canvas view for graph/content visualization