"""Check actual generated Python without allowing imports, calls or other effects."""
import ast
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
blocks = re.findall(r'```(?:python)?\s*\n([\s\S]*?)```', source)
code = blocks[0] if blocks else source.strip()
tree = ast.parse(code)
allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
           ast.BinOp, ast.Add, ast.Name, ast.Load, ast.Constant, ast.Expr)
assert all(isinstance(node, allowed) for node in ast.walk(tree)), source
assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
function = tree.body[0]
assert function.name == 'add' and not function.decorator_list
assert [arg.arg for arg in function.args.args] == ['a', 'b']
assert not function.args.defaults and not function.args.kw_defaults
assert not function.args.vararg and not function.args.kwarg
scope = {'__builtins__': {}, 'int': int, 'float': float}
exec(compile(tree, '<generated-pure-function>', 'exec'), scope)
for a, b in ((2, 3), (-7, 2), (0, 0), (10**20, 3)):
    assert scope['add'](a, b) == a+b, source
print('PASS: real generated function adds positive, negative, zero and large integers')
