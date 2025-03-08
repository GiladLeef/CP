# ast.py
class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, functions, classes):
        self.functions = functions
        self.classes = classes

class Function(ASTNode):
    def __init__(self, name, body):
        self.name = name
        self.body = body

class Return(ASTNode):
    def __init__(self, expr):
        self.expr = expr

class ExpressionStatement(ASTNode):
    def __init__(self, expr):
        self.expr = expr

class VarDecl(ASTNode):
    def __init__(self, name, init, datatype_name=None):
        self.name = name
        self.init = init
        self.datatype_name = datatype_name

class BinOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

class Num(ASTNode):
    def __init__(self, value):
        self.value = int(value)

class FloatNum(ASTNode):
    def __init__(self, value):
        self.value = float(value)

class Var(ASTNode):
    def __init__(self, name):
        self.name = name

class String(ASTNode):
    def __init__(self, value):
        self.value = value

class Char(ASTNode):
    def __init__(self, value):
        self.value = value

class FunctionCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

class ClassDecl(ASTNode):
    def __init__(self, name, members):
        self.name = name
        self.members = members

class MemberAccess(ASTNode):
    def __init__(self, object_expr, member_name):
        self.object_expr = object_expr
        self.member_name = member_name

class Assign(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class If(ASTNode):
    def __init__(self, condition, then_branch, else_branch):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class While(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class For(ASTNode):
    def __init__(self, init, condition, increment, body):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.body = body

class DoWhile(ASTNode):
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition
