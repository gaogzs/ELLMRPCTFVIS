import os
from z3 import *
from lark import Lark, Transformer, v_args

# Load grammar

class FOLParsingError(Exception):
    pass

def close_brackets(formula_str):
    open_count = formula_str.count('(')
    close_count = formula_str.count(')')
    difference = open_count - close_count
    if difference > 0:
        return formula_str + (')' * (difference))
    return formula_str

class IdCollector(Transformer):
    def __init__(self):
        self.variables = set()
        self.functions = set()
        
    def formula(self, args):
        return None
    def var_list(self, args):
        return [str(tok) for tok in args]
    def forall(self, args):
        vars, body = args
        for v in vars:
            self.variables.add(v)
        
    def exists(self, args):
        vars, body = args
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

def collect_iden(formula_str):
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    grammar_path = os.path.join(cur_dir, "fol.lark")
    with open(grammar_path, 'r') as f:
        grammar = f.read()
    parser = Lark(grammar, start='formula', parser='earley', lexer='dynamic')
    tree = parser.parse(formula_str)
    collector = IdCollector()
    collector.transform(tree)
    return list(collector.variables), list(collector.functions)

class Z3Builder(Transformer):
    def __init__(self, get_fun, ctx):
        self.get_fun = get_fun
        self.ctx = ctx
        
    def formula(self, args):
        return args[0]
    
    def var_list(self, args):
        return [self.var(tok) for tok in args]
    
    def forall(self, args):
        vars, body = args
        return ForAll(vars, body)
        
    def exists(self, args):
        vars, body = args
        return Exists(vars, body)
        
    def land(self, args):
        return And(*args)
    
    def lor(self, args):
        return Or(*args)
    
    def imply(self, args):
        return Implies(args[0], args[1], ctx=self.ctx)
    
    def iff(self, args):
        return args[0] == args[1]
    
    def lnot(self, args):
        return Not(args[0], ctx=self.ctx)
    
    def relation(self, args):
        a, op, b = args
        return op(a, b)
    
    def le(self, _): return lambda a,b: a<=b
    def ge(self, _): return lambda a,b: a>=b
    def lt(self, _): return lambda a,b: a<b
    def gt(self, _): return lambda a,b: a>b
    def eq(self, _): return lambda a,b: a==b
    def ne(self, _): return lambda a,b: a!=b
    
    @v_args(inline=True)
    def var(self, name):
        return Int(str(name), ctx=self.ctx)
    @v_args(inline=True)
    def const(self, tok):
        return IntVal(int(tok), ctx=self.ctx)
    @v_args(inline=True)
    def func(self, name, terms):
        terms_children = terms.children
        z3_func = self.get_fun(str(name))
        if z3_func is None:
            raise FOLParsingError(f"Function {name}() not found in function table. Please remove any references to it and do not add in anything else.")
        try:
            contructed_func = z3_func(*terms_children)
        except Exception as e:
            raise FOLParsingError(f"Error constructing function {name} with arguments {terms_children}: {e}")
        return contructed_func

def parse_z3(builder, formula_str):
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    grammar_path = os.path.join(cur_dir, "fol.lark")
    with open(grammar_path, 'r') as f:
        grammar = f.read()
    parser = Lark(grammar, start='formula', parser='earley', lexer='dynamic')
    if "'" in formula_str or '"' in formula_str:
        raise FOLParsingError(f"Formula should not contain strings: {formula_str}")
    formula_str = close_brackets(formula_str)
    try:
        tree = parser.parse(formula_str)
    except Exception as e:
        raise FOLParsingError(f"Syntax error when parsing formula: {formula_str} {e}")
    try:
        built_formula = builder.transform(tree)
    except Exception as e:
        raise FOLParsingError(f"Error when building formula: {formula_str} {e}")
    return built_formula