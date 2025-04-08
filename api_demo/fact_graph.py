import networkx as nx
import random

desc_node_types = """
**FactNode Types**
This is a description of types of nodes in the graph. This describes the nature of the object represented by the node itself.
-\"character\": A character in the role-playing that can interact with the user. Example: \"A brave knight\", \"Napoleon Bonaparte\", \"The narrator\".
-\"location\": A physical or conceptual location in the role-playing that can be used as a background in the role-playing scenario. Example: \"A dark forest\", \"Paris\", \"Your bedroom\".
-\"item\": An inanimate item that exists in the role-playing. It can be a weapon, a tool, or any other object. Example: \"A sword\", \"'The Art of War' the book\", \"A rock blocking the road\".
-\"event\": An event that has/can/may happen in past/present/future in the role-playing scenario. Example: \"A dragon attack\", \"A birthday party\", \"A car accident\".
-\"concept\": A notable concept that is important in the role-playing scenario. It can be a theory, a philosophy, or any other abstract idea. Example: \"The concept of time\", \"The theory of relativity\", \"The idea of freedom\".
"""

desc_info_types = """
**Information Types**
This is a description of types of information, it is another type of category for a node in the graph. This describes the nature of the information contained by the node itself.
-\"ExistingReal\": Existing real and known objects, their information should, can be, and will be easily retrieved by LLMs at once. While evaluating nodes like this, you should actively fetch and present the information that is not implicitly stated in the conversation or graph. Example: Example: Napoleon Bonaparte, The Art of War, Paris.
-\"ExistingFictional\": Existing fictional objects, they should also have public available information, but may not be as abundant as a real object. When evaluating nodes like this, you should actively fetch and present the information that is not implicitly stated in the conversation or graph, but treat them less strict than real ones since they are fictional afterall. Example: Harry Potter, The Matrix, Telescreens.
-\"Original\": An object that has been originally created in this role-playing scenario, and has not existed in the public knowledge before. When evaluating nodes like this, you should actively make use of the information that is implicitly stated in the conversation or graph. Example: A dragon, A magic spell, The 6th industrial revolution.
-\"ExistingUnkown\": An object who is suppposed to be real but not famous enough to be recognised using public information. When evaluating nodes like this, you you should actively make use of the information that is implicitly stated in the conversation or graph, while also make use of common sense and general knowledge in the real world. Example: A random real person, An real village not on most maps, The apple I ate this morning.
-\"Random\": A vaguely defined object that has very little information. As there will not be much implicit information regarding such objects, you should predict further information using the context. Example: The person you just ran into, The road you just walked by.
-\"Abstract\": A vaguely defined object. In this case, the object is not supposed to be developed too deep, and should be restricted at its behaviour before. Example: The narrator, The user, The system.
"""
desc_edge_content = """
**Edge Content**
All edges are directed in this graph. An edge must contain an non-empty content. The content of an edge can be anything, that is a brief description of the relationship between the two nodes. The content should be one short sentence, as an directed edge, it should use placeholder \"[source_node]\" to indicate the source node, and \"[target_node]\" to indicate the target node in the sentence.
For example, \"[source_node] is a friend of [target_node]\", \"[source_node] is living in [target_node]\", \"[source_node] do not believe [target_node]\".
"""

class FactNode:
    def __init__(self, node_id: int, node_name: str, node_type: str, info_type: str, description: str):
        self.node_id = node_id
        self.node_name = node_name
        self.node_type = node_type
        self.info_type = info_type
        self.description = description

    def __repr__(self):
        return f"{self.node_id}(node_type={self.node_type}, info_type={self.info_type}, description={self.description})"

class FactGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_types = {"character", "location", "item", "event", "concept"}
        self.info_types = {"ExistingReal", "ExistingFictional", "Original", "ExistingUnknown", "Random", "Abstract"}
        self.node_id_counter = 0
        self.node_id_map = {}
    
    def append_node(self, node_name: str, node_type: str, info_type: str, description: str) -> int:
        if node_type not in self.node_types:
            raise ValueError(f"Invalid node type: {node_type}. Valid types are: {self.node_types}")
        if info_type not in self.info_types:
            raise ValueError(f"Invalid info type: {info_type}. Valid types are: {self.info_types}")
        
        node_id = self.node_id_counter
        self.node_id_counter += 1
        
        node = FactNode(node_id, node_name, node_type, info_type, description)
        self.graph.add_node(node=node)
        self.node_id_map[node_name] = node
        
        return node_id
    
    def append_edge(self, source_node_name: str, target_node_name: str, content: str) -> None:
        if source_node_name not in self.node_id_map:
            raise ValueError(f"Source node {source_node_name} does not exist.")
        if target_node_name not in self.node_id_map:
            raise ValueError(f"Target node {target_node_name} does not exist.")
        
        source_node = self.node_id_map[source_node_name]
        target_node = self.node_id_map[target_node_name]
        
        self.graph.add_edge(source_node, target_node, content=content)
    
    def edit_node(self, node_name: str, attribute_name: str, target_value) -> None:
        if node_name not in self.node_id_map:
            raise ValueError(f"FactNode {node_name} does not exist.")
        
        node = self.node_id_map[node_name]
        
        if attribute_name == "node_name":
            if target_value in self.node_id_map:
                raise ValueError(f"FactNode name {target_value} already exists.")
            del self.node_id_map[node_name]
            node.node_name = target_value
            self.node_id_map[target_value] = node
        elif attribute_name == "node_type":
            if target_value not in self.node_types:
                raise ValueError(f"Invalid node type: {target_value}. Valid types are: {self.node_types}")
            node.node_type = target_value
        elif attribute_name == "info_type":
            if target_value not in self.info_types:
                raise ValueError(f"Invalid info type: {target_value}. Valid types are: {self.info_types}")
            node.info_type = target_value
        elif attribute_name == "description":
            node.description = target_value
        else:
            raise ValueError(f"Invalid attribute name: {attribute_name}. Valid attributes are: node_type, info_type, description")
    
    def edit_edge(self, source_node_name: str, target_node_name: str, content: str) -> None:
        if source_node_name not in self.node_id_map:
            raise ValueError(f"Source node {source_node_name} does not exist.")
        if target_node_name not in self.node_id_map:
            raise ValueError(f"Target node {target_node_name} does not exist.")
        
        source_node = self.node_id_map[source_node_name]
        target_node = self.node_id_map[target_node_name]
        
        if not self.graph.has_edge(source_node, target_node):
            raise ValueError(f"No edge exists between {source_node_name} and {target_node_name}.")
        
        self.graph[source_node][target_node]['content'] = content
    
    def remove_node(self, node_name: str) -> None:
        if node_name not in self.node_id_map:
            raise ValueError(f"FactNode {node_name} does not exist.")
        
        node = self.node_id_map[node_name]
        self.graph.remove_node(node)
        del self.node_id_map[node_name]
    
    def remove_edge(self, source_node_name: str, target_node_name: str) -> None:
        if source_node_name not in self.node_id_map:
            raise ValueError(f"Source node {source_node_name} does not exist.")
        if target_node_name not in self.node_id_map:
            raise ValueError(f"Target node {target_node_name} does not exist.")
        
        source_node = self.node_id_map[source_node_name]
        target_node = self.node_id_map[target_node_name]
        
        self.graph.remove_edge(source_node, target_node)
    
    def get_node(self, node_name: str) -> tuple[FactNode, list, list]:
        if node_name not in self.node_id_map:
            raise ValueError(f"FactNode {node_name} does not exist.")
        node = self.node_id_map[node_name]
        in_edges = list(self.graph.in_edges(node, data=True))
        out_edges = list(self.graph.out_edges(node, data=True))
        return node, in_edges, out_edges
    
    def sample_edges(self, num_edges: int) -> list:
        if num_edges <= 0:
            raise ValueError("Number of edges must be positive.")
        if num_edges > self.graph.number_of_edges():
            raise ValueError("Number of edges exceeds the number of edges in the graph.")
        
        edges = random.sample(self.graph.edges(data=True), num_edges)
        return edges
    
    def sample_false_edges(self, num_edges: int) -> list:
        if num_edges <= 0:
            raise ValueError("Number of edges must be positive.")
        
        false_edges = []
        all_nodes = list(self.graph.nodes())
        while len(false_edges) < num_edges:
            source_node = random.choice(all_nodes)
            target_node = random.choice(all_nodes)
            if source_node != target_node and not self.graph.has_edge(source_node, target_node):
                false_edges.append((source_node, target_node))
        
        return false_edges

    def exec_function(self, function_name: str, kwargs: dict):
        if function_name == "append_node":
            return self.append_node(**kwargs)
        elif function_name == "append_edge":
            return self.append_edge(**kwargs)
        elif function_name == "edit_node":
            return self.edit_node(**kwargs)
        elif function_name == "edit_edge":
            return self.edit_edge(**kwargs)
        elif function_name == "remove_node":
            return self.remove_node(**kwargs)
        elif function_name == "remove_edge":
            return self.remove_edge(**kwargs)
        else:
            raise ValueError(f"Function {function_name} not recognized.")

tool_api = tools = [
{
    "type": "function",
    "name": "append_node",
    "description": "Append a new node to the graph.",
    "parameters": {
        "type": "object",
        "properties": {
            "node_name": {
                "type": "string",
                "description": "The name of the object represented by the node."
            },
            "node_type": {
                "type": "string",
                "description": desc_node_types,
                "enum": ["character", "location", "item", "event", "concept"]
            },
            "info_type": {
                "type": "string",
                "description": desc_info_types,
                "enum": ["ExistingReal", "ExistingFictional", "Original", "ExistingUnknown", "Random", "Abstract"]
            },
            "description": {
                "type": "string",
                "description": "Any additional description of the node. This could be empty if not needed."
            }
        },
        "required": ["node_name", "node_type", "info_type", "description"],
        "additionalProperties": False,
    },
    "strict": True
},
{
    "type": "function",
    "name": "append_edge",
    "description": "Append a new edge to the graph.",
    "parameters": {
        "type": "object",
        "properties": {
            "source_node_name": {
                "type": "string",
                "description": "The name of the source node of the new edge."
            },
            "target_node_name": {
                "type": "string",
                "description": "The name of the target node of the new edge."
            },
            "content": {
                "type": "string",
                "description": desc_edge_content
            }
        },
        "required": ["source_node_name", "target_node_name", "content"],
        "additionalProperties": False,
    },
    "strict": True
},
{
    "type": "function",
    "name": "edit_node",
    "description": "Edit a node in the graph.",
    "parameters": {
        "type": "object",
        "properties": {
            "node_name": {
                "type": "string",
                "description": "The name of the node to be edited. Used to find the node."
            },
            "attribute_name": {
                "type": "string",
                "description": "The attribute you want to edit.",
                "enum": ["node_name", "node_type", "info_type", "description"]
            },
            "target_value": {
                "type": ["string", "number"],
                "description": "The new value for the attribute."
            }
        },
        "required": ["node_name", "attribute_name", "target_value"],
        "additionalProperties": False,
    },
    "strict": True
},
{
    "type": "function",
    "name": "edit_edge",
    "description": "Edit the content of an edge in the graph.",
    "parameters": {
        "type": "object",
        "properties": {
            "source_node_name": {
                "type": "string",
                "description": "The name of the source node. Used to find the edge."
            },
            "target_node_name": {
                "type": "string",
                "description": "The name of the target node. Used to find the edge"
            },
            "content": {
                "type": "string",
                "description": desc_edge_content
            }
        },
        "required": ["source_node_name", "target_node_name", "content"],
        "additionalProperties": False,
    },
    "strict": True
},
{
    "type": "function",
    "name": "remove_node",
    "description": "Remove a node from the graph.",
    "parameters": {
        "type": "object",
        "properties": {
            "node_name": {
                "type": "string",
                "description": "The name of the node to be removed."
            }
        },
        "required": ["node_name"],
        "additionalProperties": False,
    },
    "strict": True
},
{
    "type": "function",
    "name": "remove_edge",
    "description": "Remove an edge from the graph.",
    "parameters": {
        "type": "object",
        "properties": {
            "source_node_name": {
                "type": "string",
                "description": "The name of the source node. Used to find the edge."
            },
            "target_node_name": {
                "type": "string",
                "description": "The name of the target node. Used to find the edge"
            }
        },
        "required": ["source_node_name", "target_node_name"],
        "additionalProperties": False,
    },
    "strict": True
}
]