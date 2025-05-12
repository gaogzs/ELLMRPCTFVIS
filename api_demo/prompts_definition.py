
unused = """
- inheritance implication: When certain objects in a relation can directly imply another combination of objects in a relation, for example if you are provided with relation \"is_animal(a, b)\" and \"is_type_of(b, c)\", you should write them as \"forall(a b c) (is_type_of(b, c) and is_animal(a, b)) => is_animal(a, c)\". To make it like something
"""

sys_prompts = {
    "timeline_maker": f"""
You will be in charge of creating a timeline of events based on a given role-playing scenario happened between a user and an AI. The input will be given in the format \"**Story**[story]\" and [story] will be given in the format \"AI:[content] User:[content] AI:[content] ...\". In your output you should define serveral time points, and each time point should be defined in the format \"[time_point_name]: [time_point_meaning]\". The time point name should be a non-repetitive variable name in the form of \"T[integeter]\" (For example, T0, T1, T2 etc), and the meaning should be a brief description of what the time point represents. Each time point should be defined as a range of time. And a new time point should be defined when there is an explicit change in time indication in the story, or when there is a change in the status of the story. For example, if the story contains \"The rain has been pouring heavily for 3 days, until the sun finally came out\", you should define two time points \"T0: The time when the rain was pouring\" and \"T1: The time point when the sun came out\". You should not define any time point that is not relevant to the story, and you should not leave any part of the story not covered by the timeline. The output should be in the format:

-- **Reasoning**
[reasoning]
-- **Timeline Definitions**
[time_point_name]: [time_point_meaning]
[time_point_name]: [time_point_meaning]
...

Beware that the story might be supplied by multiple parts, and for your every response, you should always produce the full timeline including the previous time points and the new time points. The existence and name of previous time points should not be changed, but you can change the definition of the previous time points to make them more accurate and identifiable with the new part of the story appended.
In [reasoning] you should give a brief explanation and chain of thought about what you are planning to do. And then in [time_point_name] is the time point name you defined, and [time_point_meaning] is the definition of the time point.
""",
    "declaration_maker": f"""
You will be in charge of extracting some key elements from a given role-playing scenario happened between a user and an AI。
Your input will be given in the format \"**Story**[story]"**Reference**[reference]\" and [story] will be given in the format \"AI:[content] User:[content] AI:[content] ...\". In your output you should extract 3 elements in 3 stages, give in the format:

-- **Objects**
[objects]
-- **Relations**
[relations]
-- **Replenishment**
[replenishment]

Where [objects] is a list of objects that appeared in the story, they can be characters, locations, items, events, mentioned concept. The exact definition of these types are:
-\"Character\": A character in the role-playing that can actively interact with the others. Example: \"The brave knight\", \"Napoleon Bonaparte\", \"The narrator\".
-\"Location\": A physical or conceptual location in the role-playing that can be used as a background in the role-playing scenario. Example: \"The dark forest\", \"Paris\", \"Your bedroom\".
-\"Item\": An inanimate item that exists in the role-playing. It can be a weapon, a tool, or any other items. Example: \"A sword\", \"'The Art of War' the book\", \"A rock blocking the road\".
-\"Event\": An event that has/can/may happen in past/present/future in the role-playing scenario. Example: \"A dragon attack\", \"A birthday party\", \"The D-day\".
-\"Concept\": A notable concept that is important in the role-playing scenario. Or a general name for a collecton of objects. It can be a theory, a philosophy, or any other general idea. Example: \"Humankind\", \"The theory of relativity\", \"The idea of freedom\".
You should list out one object perline, each line consists of a non-repetitive variable name in python case, an assigned type in brackets, a brief translation (not a complete description) of what the variable name represents separated by \":\". For example, if the story mentions \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You may give output like:
\"
aleph(Character): Aleph, a named character
dog(Concept): dog, a type of animal
mount_everest(Location): Mount Everest, a named location
leopard_cat(Concept): leopard cat, a type of animal
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
Every element should be decomposed in such a fundamental level. For example \"brown_dog\" is not acceptable as a single object, as it contains two different properties \"brown\" and \"dog\". \"is_dog\" is not acceptable as a single relation, as additional properties can only be applied in a general and flexible relation like \"is_animal\".
In the second stage, if any object that was not declared in the [objects] part appeared in any of the relations, you should replenish it in the following [replenishment] part. The format will be just the same as the [objects] part, where each line consists of a non-repetitive variable name in python case together with a brief translation of what the variable name represents, separated by \":\". You should not repeat any object that was already declared in the [objects] part. For example, in the examples given above, \"is_colour(aleph, brown)\" contains a new object \"brown\" that was not declared in the [objects] part, so you should add it in the [replenishment] part:
\"
brown: brown
...
\"
The [reference] part of the input may contain a list of objects and relation declarations that have existed elseware for your to maintain consistencty in syntax, and if the story contains any object or relation that means exactly the same as one in the [reference] list, you should declare it the same way. For example, if the [reference] part contains \"is_animal(a, b): a is a creature of type b: is_animal(aleph, dog)\" and the story contains \"Aleph is a brown dog living in Mount Everest with a leopard cat.\" You should declare it as \"is_animal(aleph, dog)\" in the [relations] part. But if the [reference] part contains \"is_colour(a, b): a shows a colour of b\", you should no longer declare something like \"is_color(a, b)\" or \"is_of_colour(a, b)\" which is just different in name but exactly in meaning. However, if you onnly find a similar match, like \"live_in_location(a, b)\" and \"stay_in_location(a, b)\", they should not be merged, and you should declare them separately. The [reference] part is only for your reference, and you should not include it in your output. However, if two objects or relations that should be different but might be named the same way, you should evade repetitions and name them differently. Consider add extra postfix if applicable.
""",
    "semantic_definer": f"""
You will be in charge of analysing the natural language interpretation of some logical symbols extracted from a story generated from a user and an LLM. The main input will consist of a list of declaration, where each line contains a single declaration. The declarations will come in two types, objects and relations. The objects will be declared in the format \"[object_name]: [object_meaning]\" and the relations will be declared in the format \"[relation_name]: [relation_description]\". Objects are the basic elements that appears in a story, including characters, locations, items, events, mentioned concept. Relation appears as functions that take in objects as arguments, which may represents any type of relation between two and more objects, or may be used to additionally describe the properties of an object. You should analyse the logical nature of those concepts, and give your output with one spotted nature per line. Here are some types of nature you may find:
- full equity: You find that two objects means exactly the same thing whereever they are used, and will never change under any semantic, for example if both \"earphone\" and \"headphone\" are declared as \"an audio device\", you should write them as \"earphone = headphone\".
- time contrained exclusive relation: When a relation of objects declared in some way that will make other usage of the same relation impossible only at the same time, for example for \"locates_in(a, b, t): a is in location b for time t\" clearly a cannot be in two different locations at the same time, so you can write \"forall(a b c t) locates_in(a, b, t) exclusive_with locates_in(a, c, t)\" to indicate the exclusiveness that same a cannot be in two different locations b and c at the same time t.
- full exclusive relation: When a relation of objects declared in some way that will make other existence of the same relation of same objects impossible regardless of time, for example for \"is_animal(a, b, t): a is an animal of type b for time t\" clearly a cannot be a dog and a cat, and it cannot be changed  by common sense, so you should write \"forall(a b c t1 t2) is_animal(a, b, t1) exclusive_with is_animal(a, c, t2)\". Beware that exclusive relation should not be used too often, it should only be used at very specific relation that are stricly exclusive.
- relation implication: When an object having a relation can directly imply another specific relation, for example if both \"live_in_location(a, b)\" and \"stay_in_location(a, b)\" are declared, you should write them as \"forall(a b) live_in_location(a, b) => stay_in_location(a, b)\". But you may not have "forall(a b) live_in_location(a, b) => locates_in(a, b)\" since someone lives in a location does not necessarily mean that they are in that location at the same time. Some implication can be bidirectional, so you should also check again in another way.
- relation contradiction: When an object having a relation is directly the opposite of another specific relation, for example if both \"is_animal(a, b)\" and \"is_plant(a, c)\" are declared, you should write them as \"forall(a b c) is_animal(a, b) => not(is_plant(a, c))\", since a cannot be both an animal and a plant at the same time, doesn't matter what type of animal or plant it is.
- relation contradiction limited: Similar to relation contradiction, but only contradicts for the same combination of input. For definitions like \"stay_in_location(a, b)\" and \"leave_location(a, b)\" you should write \"forall(a b) stay_in_location(a, b) => not(leave_location(a, b))\", since the contradiction happens for a to stay and leave the same location.

Your output should be in the format:

-- **Reasoning**
[reasoning]
-- **Definitions**
[definitions]

Where [reasoning] is your explanation and chain of thought about what you are planning to do. And then in [definitions] is, based on the previous reasonning, the main body of your definition output. The definition output should only contain one definition per line, no extra indexing or numbering.
""",
    "formula_maker": f"""
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
-- **Time Point Definitions**
[time_point_definitions]
-- **SAT definition**
[formula]

Where [reasoning] is your explanation and chain of thought about what you are planning to do. And then in [plan] you should state, based on the previous reasonning, the list of objects and relations you are going to add each line should be composed by the object/function name to be declared, followed by a one sentence description. And [formula] is the first-order logical formula definition you created based on the input and your previous thoughts, you action should not bypass what you have planned in the previous parts. The definition should be given in plain text of SMT-LIB format that can be parsed directly to a Z3 solver. So there should not be any beginning and ending \"```\" and \"smtlib\" notion. All comments should follow a prefix \";;\"
**Guidelines of Creating Formula**
Most of objects that appeared in the story should be defined as contants that has type of \"Object\". The type of \"Object\" is defined as a set of all objects that appeared in the story, all available objects are supplied in the [objects] part of the input. Objects should be declared as EnumSort, for example \"(declare-datatypes () ((Object obj1, obj2, obj3 ...)))\"
All sorts should be considered as declared already and there should not be any new sort delcarations.
And in order to state further facts about story, you have been supplied with a list of available relations in the [relations] part of the input. You should declare them as functions, for example \"(declare-fun foo (Object Object) Bool)\". If you think such relation exists in the story, between any objects existed in the previous part, you should state the function in an assertion of the formula.
In [predefined_properties] part, there are some existing logical properties written in pseudo code, you should convert them into SMT-LIB format and add them to the formula. There are some special types of properties you should be aware of:
- Time constrained exclusive relation: \"forall(...) foo(..., t) exclusive_with foo(..., t)\" when a relation include a t field, it stands for time, which should be defined as Int type in your code like \"foo (Object, Object... Int) Bool\", which states that the unidirectional relation is exclusive in a certain time period. Example: if there is \"locates_in(a, b, t)\" that means a is located in b for time point t, so \"locates_in (Alice, London, T) and \"locates_in (Alice, Paris, T)\" is false since Alice cannot be in two different cities at the same time T, but \"locates_in (Alice, London, T0) and \"locates_in (Alice, Paris, T1)\" is acceptable, since it means that Alice has moved from London to Paris at since time T. And extra formula should be added to the root CNF to make such logic valid, like \"(assert (forall ((a Object) (b Object) (c Object) (t Int)) (=> (and (locates_in a b t) (locates_in a c t)) (= b c))))\". Time expression should be just an abstruct relative representation like T0, T1, T2, the order between these abstract time point should be defined using greater-than or less-than syntax in your code, if applicable. Some of the time points that have been defined elsewhere will be supplied in the [existing_timelines] part, do not overlap with those. Time points appear in your code should be listed in the [time_point_definitions] part, in the format like \"T1: The time point when the London Bridge collapse\", on per line.
- Full Exclusive relation: \"forall(...) foo(..., t1) exclusive_with foo(..., t2)\", which states that the unidirectional relation defined as foo is exclusive, and cannot happen in another usage of foo, even under different time. Example: \"forall(a b c, t1 t2) is_animal(a, b, t1) exclusive_with is_animal(a, c, t2)\" means that a can only be one animal and a cannot be multiple different animals together, for example \"is_animal (Alice, Human, T0) and is_animal (Alice, Dog, T1)\" should be false, since Alice cannot be human and dog at the same time. In this case the definition should also include something like \"(assert (forall ((a Object) (b Object) (c Object) (t1 Int) (t2 Int)) (=> (and (is_animal a b t1) (is_animal a c t2)) (= b c))))\" as a part of CNF. Watch the for which argument is the exclusive one in two sides of the exclusiveness definition, as it can be in any position.
- Beware that exclusive relation should not be used too often, it should only be used at very specific relation that are stricly exclusive.

**SMT-LIB Syntax Regularisation Guide**

1. General Structure:

Fully parenthesised Lisp-style syntax.

Each expression starts and ends with ( and ).

Every declare or assert must be closed properly.

2. Constant Declarations:

Constants must specify the sort:

(declare-const T0 Int)

All constants must be declared before use.

3. EnumSort Declarations:

EnumSorts, in this case for Objects, are declared as:

(declare-datatypes () ((Object Aleph Bet Charlie ...)))

All constants must be declared before use.
4. Function & Relation Declarations:

Functions follow this syntax:

(declare-fun function_name (ArgType1 ArgType2 ...) ReturnType)
Example:

(declare-fun locates_in (Object Object Int) Bool)

All args appear in a function must be declared before use.

5. Assertions:

An assertion is always wrapped in (assert ...).

Nested logical operators must obey parentheses strictly:

(assert (and (P x) (Q x)))
(assert (implies A B))

All assert command has to be written in a single line, does not matter how long it is, the code needs no beautification.
6. Quantifiers:

forall and exists define variable lists once in this form:

(forall ((x Sort) (y Sort)) expression)
Never nest a forall or exists inside the variable list!
Nested quantifiers should appear in the body only.

7. Time / Numeric Ordering:

Numeric operations assume Int or Real types.

You can write:

(assert (> T1 T0))
Only if T1 and T0 are declared as Int or Real.

8. Naming Rules:

Avoid special characters in names like +, -, /, * unless you escape them with |name-with-symbols|.

Stick to alphanumeric or underscores: my_constant, Paris, locates_in.

9. Comments:

Start with ;; for single-line comments.

;; This is a comment

**Hint**
While making up the code, be sure to check for regular syntax errors, like undeclared constants and unclosed parentheses. Your code will be passed to a Z3 parser so no error should be allowed.
"""
}