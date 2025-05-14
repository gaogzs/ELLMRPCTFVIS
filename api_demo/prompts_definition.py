
unused = """
- inheritance implication: When certain objects in a relation can directly imply another combination of objects in a relation, for example if you are provided with relation \"is_animal(a, b)\" and \"is_type_of(b, c)\", you should write them as \"forall(a b c) (is_type_of(b, c) and is_animal(a, b)) => is_animal(a, c)\". To make it like something
"""

sys_prompts = {
    "timeline_maker": """
You will be in charge of creating a timeline of events based on a given role-playing scenario happened between a user and an AI. The input will be given in the format \"**Story**[story]\" and [story] will be given in the format \"AI:[content] User:[content] AI:[content] ...\". In your output you should define serveral time points, and each time point should be defined in the format \"[time_point_name]: [time_point_meaning]\". The time point name should be a non-repetitive variable name in the form of \"T[integeter]\" (For example, T0, T1, T2 etc), and the meaning should be a brief description of what the time point represents. Each time point should be defined as a range of time. And a new time point should be defined when there is an explicit change in time indication in the story, or when there is a change in the status of the story. For example, if the story contains \"The rain has been pouring heavily for 3 days, until the sun finally came out\", you should define two time points \"T0: The time before the rain was pouring\", \"T1: The 3 days when the rain was pouring\" and \"T2: The time point when the sun came out\". You should not define any time point that is not relevant to the story, and you should not leave any part of the story not covered by the timeline, including the time before the earliest part of the story began. The output should be in the format:

-- **Reasoning**
[reasoning]
-- **Timeline Definitions**
[time_point_name]: [time_point_meaning]
[time_point_name]: [time_point_meaning]
...

Beware that the story might be supplied by multiple parts, and for your every response, you should always produce the full timeline including the previous time points and the new time points. The existence and name of previous time points should not be changed, but you can change the definition of the previous time points to make them more accurate and identifiable with the new part of the story appended. If you want to further divide existing time points, you have to declare new timpoints and explicitly defined them to be between some of the existing time points. For example, if you have already defined \"T0: The time before the rain was pouring\" and \"T1: The 3 days when the rain was pouring\" and \"T2: The time point when the sun came out\", and then you are given a new part of the story \"By the second day, the sky turned so dark that...\" you should define a new time point \"T3: The second day when the rain was pouring\".
""",
    "declaration_maker": """
You will be in charge of extracting some key elements from a given role-playing scenario happened between a user and an AI。
Your input will be given in the format \"**Story**[story]"**Reference**[reference]\" and [story] will be given in the format \"AI:[content] User:[content] AI:[content] ...\". In your output you should extract 3 elements in 3 stages, give in the format:

-- **Objects**
[objects]
-- **Relations**
[relations]
-- **Replenishment**
[replenishment]

Where [objects] is a list of objects that appeared in the story, they can be characters, locations, items, events, mentioned concept. More detailed description of these types are:
-\"Character\": A character in the role-playing that can actively interact with the others. Example: \"The brave knight\", \"Napoleon Bonaparte\", \"The narrator\".
-\"Location\": A physical or conceptual location in the role-playing that can be used as a background in the role-playing scenario. Example: \"The dark forest\", \"Paris\", \"Your bedroom\".
-\"Item\": An inanimate item that exists in the role-playing. It can be a weapon, a tool, or any other items. Example: \"A sword\", \"'The Art of War' the book\", \"A rock blocking the road\".
-\"Event\": An event that has/can/may happen in past/present/future in the role-playing scenario. Example: \"A dragon attack\", \"A birthday party\", \"The D-day\".
-\"Concept\": A notable concept that is important in the role-playing scenario. Or a general name for a collecton of objects. It can be a theory, a philosophy, or any other general idea. Example: \"Humankind\", \"The theory of relativity\", \"The idea of freedom\".
You should list out one object perline, each line consists of a non-repetitive variable name in lower case python case and a brief translation (not a complete description) of what the variable name represents separated by \":\". For example, if the story mentions \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You may give output like:
\"
aleph: Aleph, a named character
dog: dog, a type of animal
mount_everest: Mount Everest, a named location
leopard_cat: leopard cat, a type of animal
...
\"
And [relations] is a list of potential relations that can appeared in the story. Relation may represents any type of relation between two and more objects, or may be used to additionally describe the properties and facts of an object. You should list out one relation perline, each line consists of a non-repetitive relation declaration, a brief explanation of the nature of the relation, and the cases you want to apply it to, all separated by \":\". For example, in the same story \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You may give output like:
\"
is_animal(a, b, t): a is an animal of type b for time t: is_animal(aleph, dog, T0)
is_colour(a, b, t): a shows a colour of b for time t: is_colour(aleph, brown, T0)
live_in_location(a, b, t): a lives in location b for time t: live_in_location(aleph, mount_everest, T0)
...
\"
Be note that all relation is mandatory to take a time field t at the end, even if it does not seem to be subject to time. This is because the time field t is used to indicate the time point of the relation, and it is important to keep track of the time in the role-playing scenario. The time field t will be supplied as an abstract representation in the form of \"T[integeter]\" (For example, T0, T1, T2 etc).
General terms like \"is_a()\" or \"has_a()\" are not acceptable as a relation, as they are too general and do not provide any specific information about the relation, they should reflect at least the aspect of the relation.
Every element should be decomposed in such a fundamental level. For example \"brown_dog\" is not acceptable as a single object, as it contains two different properties \"brown\" and \"dog\". \"is_dog\" is not acceptable as a single relation, as additional properties can only be applied in a general and flexible relation like \"is_animal\".
In the second stage, if any object that was not declared in the [objects] part appeared in any of the relations, you should replenish it in the following [replenishment] part. The format will be just the same as the [objects] part, where each line consists of a non-repetitive variable name in lower case python case together with a brief translation of what the variable name represents, separated by \":\". You should not repeat any object that was already declared in the [objects] part. For example, in the examples given above, \"is_colour(aleph, brown)\" contains a new object \"brown\" that was not declared in the [objects] part, so you should add it in the [replenishment] part here, and the output in this case should contain:
\"
brown: brown, a colour
...
\"
The [reference] part of the input may contain a list of objects and relation declarations that have existed elseware for your to maintain consistencty in syntax, and if the story contains any object or relation that means exactly the same as one in the [reference] list, you should declare it the same way. For example, if the [reference] part contains \"is_animal(a, b): a is a creature of type b: is_animal(aleph, dog)\" and the story contains \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You should declare it as \"is_animal(aleph, dog)\" in the [relations] part. But if the [reference] part contains \"is_colour(a, b): a shows a colour of b\", you should no longer declare something like \"is_color(a, b)\" or \"is_of_colour(a, b)\" which is just different in name but exactly in meaning. However, if you onnly find a similar match, like \"live_in_location(a, b)\" and \"stay_in_location(a, b)\", they should not be merged, and you should declare them separately. The [reference] part is only for your reference, and you should not include it in your output. However, if two objects or relations that should be different but might be named the same way, you should evade repetitions and name them differently. Consider add extra postfix if applicable.
""",
    "semantic_definer": """
You will be in charge of analysing the natural language interpretation of some logical symbols extracted from a story generated from a user and an LLM. The main input will consist of a list of declaration, where each line contains a single declaration. The declarations will come in two types, objects and relations. The objects will be declared in the format \"[object_name]: [object_meaning]\" and the relations will be declared in the format \"[relation_name]: [relation_description]\". Objects are the basic elements that appears in a story, including characters, locations, items, events, mentioned concept. Relation appears as functions that take in objects as arguments, which may represents any type of relation between two and more objects, or may be used to additionally describe the properties of an object. You should analyse the logical nature of those concepts, and give your output with one spotted nature per line. Here are some types of nature you may find:
- full equity: You find that two objects means exactly the same thing whereever they are used, and will never change under any semantic, for example if both \"earphone\" and \"headphone\" are declared as \"an audio device\", you should write them as \"earphone = headphone\".
- time contrained exclusive relation: When a relation of objects declared in some way that will make other usage of the same relation impossible only at the same time, for example for \"locates_in(a, b, t): a is in location b for time t\" clearly a cannot be in two different locations at the same time, so you can write \"locates_in(a, [exclusive_arg], t)\" to indicate the exclusiveness at the second argument that same a cannot be in two different locations b at the same time t. Beware that the time parameter here means a range of time, so only relation that represents status that would span for the entire time period and is absolutely incompatible in any other ways should be declared as time contrained exclusive relation. For example, \"eat(a, b, t): a eats b for time t\", you should not declare it as time contrained exclusive relation, although it seems someone can only eat one thing at the same time, but for a range of time, a can obviously eat different things at different time.
- full exclusive relation: When a relation of objects declared in some way that will make other existence of the same relation of same objects impossible regardless of time, for example for \"is_animal(a, b, t): a is an animal of type b for time t\" clearly a cannot be a dog and a cat, and it cannot be changed after time by common sense, so you should write \"is_animal(a, [exclusive_arg], [free_arg])\" to indicate the second argument should be exclusive for the same a, and regardless of the thirdargument. Beware that exclusive relation should not be used too often, it should only be used at very specific relation that are stricly exclusive.
- relation implication: When two relations are synonym, or an object having a relation can directly imply another specific relation, for example if both \"live_in_location(a, b)\" and \"stay_in_location(a, b)\" are declared, you should write them as \"forall(a b) live_in_location(a, b) -> stay_in_location(a, b)\". But you may not have "forall(a b) live_in_location(a, b) -> locates_in(a, b)\" since someone lives in a location does not necessarily mean that they are in that location at the same time. Some implication can be bidirectional, in that case you can use \"<->\" instead of \"->\".
- relation contradiction: When an object having a relation is the antonym, or directly imply the opposite of another specific relation, for example if both \"is_animal(a, b)\" and \"is_plant(a, c)\" are declared, you should write them as \"forall(a b c) is_animal(a, b) => not(is_plant(a, c))\", since a cannot be both an animal and a plant at the same time, doesn't matter what type of animal or plant it is.
- relation contradiction limited: Similar to relation contradiction, but only contradicts for the same combination of input. For definitions like \"stay_in_location(a, b)\" and \"leave_location(a, b)\" you should write \"forall(a b) stay_in_location(a, b) => not(leave_location(a, b))\", since the contradiction happens for a to stay and leave the same location.

Your output should be in the format:

-- **Reasoning**
[reasoning]
-- **Definitions**
[definitions]

Where [reasoning] is your explanation and chain of thought about what you are planning to do. And then in [definitions] is, based on the previous reasonning, the main body of your definition output. The definition output should only contain one definition per line, no extra indexing or numbering.
""",
    "formula_maker": """
You will be in charge of creating a first-order logical formula to describe the existence of facts and narration logic of a given role-playing scenario happened between a user and an AI, which can then be used to check the logical consistency of the story elseware (so the check for consistency itself is not your concern).
The input will be given in the format:

**Story**
[story]
**Objects**
[objects]
**Relations**
[relations]
**Pre-defined properties**
[predefined_properties]
**Existing Timeline**
[existing_timelines]

Where [story] is the content of the story you will be analysing, given in the format \"AI:[content] User:[content] AI:[content] ...\".
Your output will be in the format:

-- **Reasoning**
[reasoning]
-- **Plan**
[plan]
-- **SAT definition**
[formula]

Where [reasoning] is your explanation and chain of thought about what you are planning to do. And then in [plan] you should state, based on the previous reasonning, the list of relations and logic you are going to add. And [formula] is the first-order logical formula definition you created based on the input and your previous thoughts, you action should not bypass what you have planned in the previous parts. The definition should be given in plain text of a given FOL syntax language, with one formula of the root CNF a time. So there should not be any beginning and ending \"```\" or other extra notions.
**Guidelines of Creating Formula**
Objects are a set of all notable objects that appeared in the story, all available objects are supplied in the [objects] part of the input. In order to state further facts about story, you have been supplied with a list of available relations in the [relations] part of the input. You should use them as functions, . If you think such relation exists in the story, between any objects existed in the previous part, you should state the function in an assertion of the formula.
In [predefined_properties] part, there are some existing logical properties written in pseudo code, you should convert them into a formal FOL syntax.

Your syntax specification should be:

Logical operators:
- \"and\" \"or\" \"not\" \"->\" \"<->\"
- Example: \"a and b\", \"a or b\", \"not a\", \"a -> b\", \"a <-> b\"
The default order of precedence is:
- \"not\" > \"and\" > \"or\" > \"->\" > \"<->\"
You should use parentheses to indicate the order of precedence explicitly.

Forall and Exists:
- Example: \"forall a b c . (a and b) -> c\", \"exists a b c . (a and b) -> c\"
- You should use \"forall\" and \"exists\" to indicate the quantifier, and the variables should be separated by space. The main body of the quantifier should be separated by a dot \".\".

Functions:
- Example: \"function_name(a, b, c)\"

"""
}