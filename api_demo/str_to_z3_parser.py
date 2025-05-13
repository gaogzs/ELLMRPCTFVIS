from z3 import *

object_sort = DeclareSort('Object')
class SMIObject:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.z3_element = 