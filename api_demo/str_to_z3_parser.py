import os
from z3 import *
from lark import Lark, Transformer, v_args

# Load grammar
cur_dir = os.path.dirname(os.path.realpath(__file__))
grammar_path = os.path.join(cur_dir, "fol.lark")
with open(grammar_path, 'r') as f:
    grammar = f.read()
parser = Lark(grammar, start='formula', parser='lalr')

class IdCollector(Transformer):
    def __init__(self):
        self.variables = set()
        self.functions = set()
    def formula(self, args):
        return None
    def var_list(self, args):
        return [str(tok) for tok in args]
    def forall(self, args):
        _, vars, body = args
        for v in vars:
            self.variables.add(v)
        
    def exists(self, args):
        _, vars, body = args
        for v in vars:
            self.variables.add(v)
            
        
    def var(self, args):
        name = str(args[0])
        self.variables.add(name)
        
    def func(self, args):
        name = str(args[0])
        self.functions.add(name)
        
    
    def relation(self, args):
        return None
    def land(self, args):
        return None
    def lor(self, args):
        return None
    def imply(self, args):
        return None
    def iff(self, args):
        return None
    def lnot(self, args):
        return None

def stage1_collect(formula_str):
    tree = parser.parse(formula_str)
    collector = IdCollector()
    collector.transform(tree)
    return list(collector.variables), list(collector.functions)

class Z3Builder(Transformer):
    def __init__(self, func_table):
        self.func_table = func_table
        
    def formula(self, args):
        return args[0]
    
    def var_list(self, args):
        return [str(tok) for tok in args]
    
    def forall(self, args):
        _, vars, body = args
        zvs = [self.get_var(v) for v in vars]
        return ForAll(zvs, body)
        
    def exists(self, args):
        _, vars, body = args
        zvs = [self.get_var(v) for v in vars]
        return Exists(zvs, body)
        
    def land(self, args):
        return And(*args)
    
    def lor(self, args):
        return Or(*args)
    
    def imply(self, args):
        return Implies(args[0], args[1])
    
    def iff(self, args):
        return args[0] == args[1]
    
    def lnot(self, args):
        return Not(args[0])
    
    def relation(self, args):
        a, op, b = args; return op(a, b)
    
    def le(self, _): return lambda a,b: a<=b
    def ge(self, _): return lambda a,b: a>=b
    def lt(self, _): return lambda a,b: a<b
    def gt(self, _): return lambda a,b: a>b
    def eq(self, _): return lambda a,b: a==b
    def ne(self, _): return lambda a,b: a!=b
    
    @v_args(inline=True)
    def var(self, name):
        return Int(str(name))
    @v_args(inline=True)
    def const(self, tok):
        return IntVal(int(tok))
    def func(self, args):
        name = str(args[0])
        terms = args[1:]
        return self.get_fun(name)(*terms)

def parse_z3(formula_str, get_var, get_fun):
    tree = parser.parse(formula_str)
    builder = Z3Builder(get_var, get_fun)
    return builder.transform(tree)