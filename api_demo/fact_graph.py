import networkx as nx
import random

desc_fact_graph = """
**Graph**
This is a directed graph that represents a CONCISE summary of the current status in a role-playing scenario. The graph contains nodes and edges. Each node represents an object in the role-playing scenario, and each edge represents a relationship between two nodes.
"""

desc_fact_node = """
**Node**
This is a node in the graph. A node represents an object in the role-playing scenario. It can be a character, a location, an item, an event, or a concept. Each node has the following attributes:
-\"node_name\": The name of the object represented by the node. It is a string and should be unique in the graph. Example: \"John\", \"Paris\", \"apple\". If you have met multiple objects with the same name, you can include an attributive phrase in the name to distinguish them, both in the new one and the old one. Example: \"John (the knight)\", \"Paris (the city)\", \"apple (over there)\".
-\"node_type\": The type of the node. It can be one of the following: \"character\", \"location\", \"item\", \"event\", or \"concept\".
-\"info_type\": The type of information contained in the node. It can be one of the following: \"ExistingReal\", \"ExistingFictional\", \"Original\", \"ExistingUnknown\", \"Random\", or \"Abstract\".
-\"description\": Any additional description of the node. This should be within one sentence or empty most of the time. Example: \"the main character\", \"the first-person narrator\"
"""

desc_node_types = """
**Node Types**
This is a description of node_type attribute of a node. This describes the nature of the object represented by the node itself.
-\"character\": A character in the role-playing that can interact with the user. Example: \"A brave knight\", \"Napoleon Bonaparte\", \"The narrator\".
-\"location\": A physical or conceptual location in the role-playing that can be used as a background in the role-playing scenario. Example: \"A dark forest\", \"Paris\", \"Your bedroom\".
-\"item\": An inanimate item that exists in the role-playing. It can be a weapon, a tool, or any other object. Example: \"A sword\", \"'The Art of War' the book\", \"A rock blocking the road\".
-\"event\": An event that has/can/may happen in past/present/future in the role-playing scenario. Example: \"A dragon attack\", \"A birthday party\", \"A car accident\".
-\"concept\": A notable concept that is important in the role-playing scenario. It can be a theory, a philosophy, or any other abstract idea. Example: \"The concept of time\", \"The theory of relativity\", \"The idea of freedom\".
"""

desc_info_types = """
**Information Types**
This is a description of info_type attribute of a node,. This describes the nature of the information contained by the node itself.
-\"ExistingReal\": Existing real and known objects, their information should, can be, and will be easily retrieved by LLMs at once. While evaluating nodes like this, you should actively fetch and present the information that is not implicitly stated in the conversation or graph. Example: Example: Napoleon Bonaparte, The Art of War, Paris.
-\"ExistingFictional\": Existing fictional objects, they should also have public available information, but may not be as abundant as a real object. When evaluating nodes like this, you should actively fetch and present the information that is not implicitly stated in the conversation or graph, but treat them less strict than real ones since they are fictional afterall. Example: Harry Potter, The Matrix, Telescreens.
-\"Original\": An object that has been originally created in this role-playing scenario, and has not existed in the public knowledge before. When evaluating nodes like this, you should actively make use of the information that is implicitly stated in the conversation or graph. Example: A dragon, A magic spell, The 6th industrial revolution.
-\"ExistingUnkown\": An object who is suppposed to be real but not famous enough to be recognised using public information. When evaluating nodes like this, you you should actively make use of the information that is implicitly stated in the conversation or graph, while also make use of common sense and general knowledge in the real world. Example: A random real person, An real village not on most maps, The apple I ate this morning.
-\"Random\": A vaguely defined object that has very little information. As there will not be much implicit information regarding such objects, you should predict further information using the context. Example: The person you just ran into, The road you just walked by.
-\"Abstract\": A vaguely defined object. In this case, the object is not supposed to be developed too deep, and should be restricted at its behaviour before. Example: The narrator, The society, Science.
"""

desc_edge_content = """
**Edge Content**
All edges are directed in this graph. An edge must contain an non-empty content. The content of an edge can be anything, that is a brief description of the relationship between the two nodes. The content should be one short sentence, as an directed edge, it should use placeholder \"[source_node]\" to indicate the source node, and \"[target_node]\" to indicate the target node in the sentence.
For example, \"[source_node] is a [target_node]\", \"[source_node] is a friend of [target_node]\", \"[source_node] is living in [target_node]\", \"[source_node] do not believe in [target_node]\".
"""

class FactGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_types = {"character", "location", "item", "event", "concept"}
        self.info_types = {"ExistingReal", "ExistingFictional", "Original", "ExistingUnknown", "Random", "Abstract"}
    
    def append_node(self, node_name: str, node_type: str, info_type: str, description: str) -> None:
        if node_type not in self.node_types:
            raise ValueError(f"Invalid node type: {node_type}. Valid types are: {self.node_types}")
        if info_type not in self.info_types:
            raise ValueError(f"Invalid info type: {info_type}. Valid types are: {self.info_types}")
        if node_name in self.graph.nodes:
            raise ValueError(f"FactNode name {node_name} already exists.")
        
        self.graph.add_node(node_name, node_type=node_type, info_type=info_type, description=description)
    
    def append_edge(self, source_node_name: str, target_node_name: str, content: str) -> None:
        if source_node_name not in self.graph.nodes:
            raise ValueError(f"Source node {source_node_name} does not exist.")
        if target_node_name not in self.graph.nodes:
            raise ValueError(f"Target node {target_node_name} does not exist.")
        
        self.graph.add_edge(source_node_name, target_node_name, content=content)
    
    def edit_node(self, node_name: str, attribute_name: str, target_value) -> None:
        if node_name not in self.graph.nodes:
            raise ValueError(f"FactNode {node_name} does not exist.")
        
        if attribute_name == "node_name":
            if target_value in self.graph.nodes:
                raise ValueError(f"Node name {target_value} already exists.")
            self.graph = nx.relabel_nodes(self.graph, {node_name: target_value})
        elif attribute_name in self.graph.nodes[node_name]:
            self.graph.nodes[node_name][attribute_name] = target_value
        else:
            raise ValueError(f"Invalid attribute name: {attribute_name}. Valid attributes are: node_name, node_type, info_type, description")  
    
    def edit_edge(self, source_node_name: str, target_node_name: str, content: str) -> None:
        if source_node_name not in self.graph.nodes:
            raise ValueError(f"Source node {source_node_name} does not exist.")
        if target_node_name not in self.graph.nodes:
            raise ValueError(f"Target node {target_node_name} does not exist.")
        
        if not self.graph.has_edge(source_node_name, target_node_name):
            raise ValueError(f"Edge from {source_node_name} to {target_node_name} does not exist.")
        self.graph[source_node_name][target_node_name]['content'] = content
    
    def remove_node(self, node_name: str) -> None:
        if node_name not in self.graph.nodes:
            raise ValueError(f"FactNode {node_name} does not exist.")
        
        self.graph.remove_node(node_name)
    
    def remove_edge(self, source_node_name: str, target_node_name: str) -> None:
        if source_node_name not in self.graph.nodes:
            raise ValueError(f"Source node {source_node_name} does not exist.")
        if target_node_name not in self.graph.nodes:
            raise ValueError(f"Target node {target_node_name} does not exist.")
        
        self.graph.remove_edge(source_node_name, target_node_name)
    
    def get_node(self, node_name: str) -> tuple[dict, list, list]:
        if node_name not in self.graph.nodes:
            raise ValueError(f"FactNode {node_name} does not exist.")
        node = self.graph.nodes[node_name]
        in_edges = list(self.graph.in_edges(node_name, data=True))
        out_edges = list(self.graph.out_edges(node_name, data=True))
        return node, in_edges, out_edges
    
    def get_node_data(self, node_name: str) -> dict:
        if node_name not in self.graph.nodes:
            raise ValueError(f"FactNode {node_name} does not exist.")
        return self.graph.nodes[node_name]
    
    def sample_nodes(self, num_nodes: int) -> list:
        if num_nodes == -1:
            return list(self.graph.nodes(data=True))
        if num_nodes <= 0:
            raise ValueError("Number of nodes must be positive.")
        if num_nodes > self.graph.number_of_nodes():
            raise ValueError("Number of nodes exceeds the number of nodes in the graph.")
        
        nodes = random.sample(self.graph.nodes(data=True), num_nodes)
        return nodes
    
    def sample_edges(self, num_edges: int) -> list:
        if num_edges == -1:
            return list(self.graph.edges(data=True))
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
    
    def print_graph(self) -> str:
        if self.graph_empty():
            return "The graph is empty."
        out_str = ""
        out_str += "\nNodes:\n"
        for node_name, node_data in self.graph.nodes(data=True):
            out_str += f"{node_name} {node_data['node_type']}\n"
        out_str += "\nEdges:\n"
        for source_node, target_node, edge_data in self.graph.edges(data=True):
            out_str += f"{source_node} -> {target_node} ({edge_data['content']})\n"
        return out_str
    
    def graph_empty(self) -> bool:
        return self.graph.number_of_nodes() == 0

tool_api = [
    {
        "type": "function",
        "function": {
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
                        "description": "Any additional description of the node. This should be within one sentence or empty most of the time."
                    }
                },
                "required": ["node_name", "node_type", "info_type", "description"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
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
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
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
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
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
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
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
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
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
                "additionalProperties": False
            },
            "strict": True
        }
    }
]