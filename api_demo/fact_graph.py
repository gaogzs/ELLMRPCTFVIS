import networkx as nx

desc_node_types = """
**Node Types**
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