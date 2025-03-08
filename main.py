import sys
import subprocess
import os
import re
from llvmlite import binding as llvm
from llvmlite import ir

class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, {self.value})"

TOKENS = [
    ('COMMENT', r'//[^\n]*'),
    ('CLASS',         r'class'),
    ('INT',           r'int'),
    ('RETURN',        r'return'),
    ('NUMBER',        r'\d+'),
    ('ID',            r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('LPAREN',        r'\('),
    ('RPAREN',        r'\)'),
    ('LBRACE',        r'\{'),
    ('RBRACE',        r'\}'),
    ('SEMICOLON',       r';'),
    ('COMMA',         r','),
    ('PLUS',          r'\+'),
    ('MINUS',         r'-'),
    ('MULT',          r'\*'),
    ('DIV',           r'/'),
    ('MOD',           r'%'),
    ('EQEQ',          r'=='),
    ('NEQ',           r'!='),
    ('LTE',           r'<='),
    ('GTE',           r'>='),
    ('EQ',            r'='),
    ('LT',            r'<'),
    ('GT',            r'>'),
    ('STRING',        r'"[^"]*"'),
    ('DOT',           r'\.'),
    ('WS',            r'\s+'),
]
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

class Var(ASTNode):
    def __init__(self, name):
        self.name = name

class String(ASTNode):
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

def lex(characters):
    pos = 0
    tokens = []
    while pos < len(characters):
        match = None
        for token_type, pattern in TOKENS:
            regex = re.compile(pattern)
            match = regex.match(characters, pos)
            if match:
                text = match.group(0)
                if token_type == 'COMMENT':
                    pos = match.end(0)
                    continue
                if token_type != 'WS':
                    if token_type == 'STRING':
                        text = text[1:-1]
                    tokens.append(Token(token_type, text))
                pos = match.end(0)
                break
        if not match:
            raise SyntaxError(f'Illegal character: {characters[pos]}')
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.class_names = set()

    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        else:
            raise SyntaxError(f"Expected token {token_type}, got {token}")

    def parse(self):
        functions = []
        classes = []
        while self.current() is not None:
            if self.current().type == 'CLASS':
                class_decl = self.parse_class_declaration()
                classes.append(class_decl)
                self.class_names.add(class_decl.name)
            elif self.current().type == 'INT':
                functions.append(self.parse_function())
            else:
                if self.current() is not None:
                    token = self.consume(self.current().type)
                else:
                    break
        return Program(functions, classes)

    def parse_class_declaration(self):
        self.consume('CLASS')
        class_name = self.consume('ID').value
        self.consume('LBRACE')
        members = []
        while self.current() and self.current().type != 'RBRACE':
            member = self.parse_declaration_member()
            if not isinstance(member, VarDecl):
                raise SyntaxError("Class members must be variable declarations")
            members.append(member)
        self.consume('RBRACE')
        return ClassDecl(class_name, members)

    def parse_declaration_member(self):
        data_type_token = self.consume('INT')
        var_name = self.consume('ID').value
        self.consume('SEMICOLON')
        return VarDecl(var_name, None, datatype_name='int')

    def parse_declaration(self):
        data_type_token = self.consume_datatype()
        var_name = self.consume('ID').value
        datatype_name = data_type_token.value
        if data_type_token.type == 'INT':
            datatype_name = 'int'

        if self.current() and self.current().type == 'EQ':
            self.consume('EQ')
            init_expr = self.parse_expression()
            self.consume('SEMICOLON')
            return VarDecl(var_name, init_expr, datatype_name=datatype_name)
        self.consume('SEMICOLON')
        return VarDecl(var_name, None, datatype_name=datatype_name)

    def parse_function(self):
        self.consume('INT')
        name = self.consume('ID').value
        self.consume('LPAREN')
        self.consume('RPAREN')
        self.consume('LBRACE')
        body = []
        while self.current() and self.current().type != 'RBRACE':
            body.append(self.parse_statement())
        self.consume('RBRACE')
        return Function(name, body)

    def parse_statement(self):
        token = self.current()
        if token.type == 'RETURN':
            return self.parse_return()
        elif token.type == 'INT' or (token.type == 'ID' and token.value in self.class_names):
            return self.parse_declaration()
        else:
            expr = self.parse_expression()
            self.consume('SEMICOLON')
            return ExpressionStatement(expr)

    def consume_datatype(self):
        token = self.current()
        if token.type == 'INT' or (token.type == 'ID' and token.value in self.class_names):
            self.pos += 1
            return token
        else:
            raise SyntaxError(f"Expected datatype (INT or Class Name), got {token}")

    def parse_return(self):
        self.consume('RETURN')
        expr = self.parse_expression()
        self.consume('SEMICOLON')
        return Return(expr)

    def parse_expression(self):
        node = self.parse_assignment()
        return node

    def parse_assignment(self):
        node = self.parse_comparison()
        if self.current() and self.current().type == 'EQ':
            op = self.consume('EQ').value
            right = self.parse_assignment()
            if isinstance(node, MemberAccess) or isinstance(node, Var):
                return Assign(node, right)
            else:
                raise SyntaxError("Invalid left-hand side for assignment")
        return node

    def parse_comparison(self):
        node = self.parse_additive_expression()
        while self.current() and self.current().type in ('EQEQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
            op_token = self.consume(self.current().type)
            op = op_token.type
            right = self.parse_additive_expression()
            node = BinOp(op, node, right)
        return node

    def parse_additive_expression(self):
        node = self.parse_multiplicative_expression()
        while self.current() and self.current().type in ('PLUS', 'MINUS'):
            op = self.consume(self.current().type).value
            right = self.parse_multiplicative_expression()
            node = BinOp(op, node, right)
        return node

    def parse_multiplicative_expression(self):
        node = self.parse_factor()
        while self.current() and self.current().type in ('MULT', 'DIV', 'MOD'):
            op = self.consume(self.current().type).value
            right = self.parse_factor()
            node = BinOp(op, node, right)
        return node

    def parse_factor(self):
        token = self.current()
        if token.type == 'NUMBER':
            self.consume('NUMBER')
            return Num(token.value)
        elif token.type == 'STRING':
            self.consume('STRING')
            return String(token.value)
        elif token.type == 'ID':
            self.consume('ID')
            name = token.value
            if self.current() and self.current().type == 'DOT':
                self.consume('DOT')
                member_name = self.consume('ID').value
                return MemberAccess(Var(name), member_name)
            elif self.current() and self.current().type == 'LPAREN':
                return self.parse_function_call(name)
            return Var(name)
        elif token.type == 'LPAREN':
            self.consume('LPAREN')
            node = self.parse_expression()
            self.consume('RPAREN')
            return node
        else:
            raise SyntaxError(f"Unexpected token: {token}")

    def parse_function_call(self, func_name):
        self.consume('LPAREN')
        args = []
        if self.current() and self.current().type != 'RPAREN':
            args.append(self.parse_expression())
            while self.current() and self.current().type == 'COMMA':
                self.consume('COMMA')
                args.append(self.parse_expression())
        self.consume('RPAREN')
        return FunctionCall(func_name, args)

class CodeGen:
    def __init__(self):
        self.module = ir.Module(name="my_module")
        self.builder = None
        self.func_symtab = {}
        self.string_counter = 0
        self.declare_print_func()
        self.program_node = None
        self.class_struct_types = {}

    def declare_print_func(self):
        print_type = ir.FunctionType(
            ir.IntType(32),
            [ir.PointerType(ir.IntType(8))],
            var_arg=True
        )
        self.print_func = ir.Function(self.module, print_type, name="printf")

    def generate_code(self, node):
        if isinstance(node, Program):
            self.program_node = node
            for node_item in node.classes + node.functions:
                if isinstance(node_item, ClassDecl):
                    self.codegen_class_declaration(node_item)
            for node_item in node.functions:
                if isinstance(node_item, Function):
                    self.codegen_function(node_item)
        return self.module

    def create_string_constant(self, string_val):
        string_bytes = bytearray((string_val + '\0').encode('utf8'))
        string_type = ir.ArrayType(ir.IntType(8), len(string_bytes))
        name = f".str.{self.string_counter}"
        self.string_counter += 1
        global_str = ir.GlobalVariable(self.module, string_type, name=name)
        global_str.global_constant = True
        global_str.linkage = 'private'
        global_str.initializer = ir.Constant(string_type, string_bytes)
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(global_str, [zero, zero], name="str")

    def codegen_function(self, node):
        func_type = ir.FunctionType(ir.IntType(32), [])
        function = ir.Function(self.module, func_type, name=node.name)
        block = function.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.func_symtab = {}
        retval = None
        for stmt in node.body:
            retval = self.codegen(stmt)
        if self.builder.block.terminator is None:
            if retval is None:
                retval = ir.Constant(ir.IntType(32), 0)
            self.builder.ret(retval)

    def codegen_class_declaration(self, node):
        class_name = node.name
        member_types = []
        member_names = []
        for member_decl in node.members:
            member_types.append(ir.IntType(32))
            member_names.append(member_decl.name)
        class_struct_type = ir.LiteralStructType(member_types)
        self.class_struct_types[class_name] = class_struct_type

    def codegen(self, node):
        if isinstance(node, Return):
            ret_val = self.codegen(node.expr)
            self.builder.ret(ret_val)
            return ret_val
        elif isinstance(node, ExpressionStatement):
            return self.codegen(node.expr)
        elif isinstance(node, VarDecl):
            var_addr = self.builder.alloca(ir.PointerType(self.class_struct_types[node.datatype_name]) if node.datatype_name in self.class_struct_types else ir.IntType(32), name=node.name)
            if node.init:
                init_val = self.codegen(node.init)
                self.builder.store(init_val, var_addr)
            self.func_symtab[node.name] = {'addr': var_addr, 'datatype_name': node.datatype_name}
            return var_addr
        elif isinstance(node, BinOp):
            left = self.codegen(node.left)
            right = self.codegen(node.right)
            if node.op == '+':
                return self.builder.add(left, right, name="addtmp")
            elif node.op == '-':
                return self.builder.sub(left, right, name="subtmp")
            elif node.op == '*':
                return self.builder.mul(left, right, name="multmp")
            elif node.op == '/':
                return self.builder.sdiv(left, right, name="divtmp")
            elif node.op == '%':
                return self.builder.srem(left, right, name="remtmp")
            elif node.op == 'EQEQ':
                bool_val = self.builder.icmp_signed("==", left, right, name="eqtmp")
                return self.builder.zext(bool_val, ir.IntType(32), name="eq_int_tmp")
            elif node.op == 'NEQ':
                bool_val = self.builder.icmp_signed("!=", left, right, name="neqtmp")
                return self.builder.zext(bool_val, ir.IntType(32), name="neq_int_tmp")
            elif node.op == 'LT':
                bool_val = self.builder.icmp_signed("<", left, right, name="lttmp")
                return self.builder.zext(bool_val, ir.IntType(32), name="lt_int_tmp")
            elif node.op == 'GT':
                bool_val = self.builder.icmp_signed(">", left, right, name="gttmp")
                return self.builder.zext(bool_val, ir.IntType(32), name="gt_int_tmp")
            elif node.op == 'LTE':
                bool_val = self.builder.icmp_signed("<=", left, right, name="letmp")
                return self.builder.zext(bool_val, ir.IntType(32), name="lte_int_tmp")
            elif node.op == 'GTE':
                bool_val = self.builder.icmp_signed(">=", left, right, name="getmp")
                return self.builder.zext(bool_val, ir.IntType(32), name="gte_int_tmp")
            else:
                raise ValueError(f"Unknown binary operator {node.op}")
        elif isinstance(node, Num):
            return ir.Constant(ir.IntType(32), node.value)
        elif isinstance(node, String):
            return self.create_string_constant(node.value)
        elif isinstance(node, Var):
            if node.name in self.func_symtab:
                return self.builder.load(self.func_symtab[node.name]['addr'], name=node.name)
            else:
                raise NameError(f"Undefined variable: {node.name}")
        elif isinstance(node, FunctionCall):
            if node.name == "print":
                return self.codegen_print_call(node)
            else:
                raise NameError(f"Unknown function: {node.name}")
        elif isinstance(node, MemberAccess):
            return self.codegen_member_access(node)
        elif isinstance(node, Assign):
            return self.codegen_assignment(node)
        else:
            raise NotImplementedError(f"Codegen not implemented for {type(node)}")

    def codegen_assignment(self, node):
        var_node = node.left
        assign_val = self.codegen(node.right)
        if isinstance(var_node, Var):
            var_info = self.func_symtab.get(var_node.name)
            if var_info is None:
                raise NameError(f"Variable '{var_node.name}' not declared.")
            var_addr = var_info['addr']
            self.builder.store(assign_val, var_addr)
            return assign_val
        elif isinstance(var_node, MemberAccess):
            return self.codegen_member_assignment(var_node, assign_val)
        else:
            raise SyntaxError("Invalid left-hand side for assignment")

    def codegen_member_access(self, node):
        object_name = node.object_expr.name
        member_name = node.member_name
        var_info = self.func_symtab[object_name]
        if var_info is None:
            raise NameError(f"Variable '{object_name}' not declared in symtab for member access.")
        class_name = var_info['datatype_name']
        class_struct_type = self.class_struct_types[class_name]
        member_index = -1
        class_decl_node = None
        for program_node in self.program_node.functions + self.program_node.classes:
            if isinstance(program_node, ClassDecl) and program_node.name == class_name:
                class_decl_node = program_node
                break
        if class_decl_node:
            for i, member in enumerate(class_decl_node.members):
                current_member_name = member_name
                if member.name == current_member_name:
                    member_index = i
                    break
        if member_index == -1:
            raise NameError(f"Member '{member_name}' not found in class '{class_name}'.")
        object_addr = var_info['addr']
        ptr = self.builder.gep(self.builder.load(object_addr), [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), member_index)], name="member_ptr")
        return self.builder.load(ptr, name=member_name)

    def codegen_member_assignment(self, member_access_node, assign_val):
        object_val = self.codegen(member_access_node.object_expr)
        member_name = member_access_node.member_name
        object_name = member_access_node.object_expr.name
        var_info = self.func_symtab[object_name]
        if var_info is None:
            raise NameError(f"Variable '{object_name}' not declared in symtab for member assignment.")
        class_name = var_info['datatype_name']
        class_struct_type = self.class_struct_types[class_name]
        member_index = -1
        class_decl_node = None
        for program_node in self.program_node.functions + self.program_node.classes:
            if isinstance(program_node, ClassDecl) and program_node.name == class_name:
                class_decl_node = program_node
                break
        if class_decl_node:
            for i, member in enumerate(class_decl_node.members):
                if member.name == member_name:
                    member_index = i
                    break
        if member_index == -1:
            raise NameError(f"Member '{member_name}' not found in class '{class_name}'.")
        object_addr = var_info['addr']
        ptr = self.builder.gep(self.builder.load(object_addr), [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), member_index)], name="member_ptr")
        self.builder.store(assign_val, ptr)
        return assign_val

    def codegen_print_call(self, node):
        format_str_parts = []
        llvm_args = []
        for arg_node in node.args:
            arg_val = self.codegen(arg_node)
            llvm_args.append(arg_val)
            if arg_val.type == ir.IntType(32):
                format_str_parts.append("%d")
            elif arg_val.type.is_pointer and arg_val.type.pointee == ir.IntType(8):
                 format_str_parts.append("%s")
            else:
                format_str_parts.append("%?")
        full_format_str = " ".join(format_str_parts) + "\n"
        llvm_format_str = self.create_string_constant(full_format_str)
        print_args = [llvm_format_str] + llvm_args
        return self.builder.call(self.print_func, print_args)

def compile_module(llvm_module, output_exe):
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    llvm_ir = str(llvm_module)
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    obj_code = target_machine.emit_object(mod)
    obj_filename = "output.o"
    with open(obj_filename, "wb") as f:
        f.write(obj_code)
    bc_filename = "output.bc"
    with open(bc_filename, 'w') as f:
        f.write(str(llvm_module))
    linked_bc_filename = "linked.bc"
    subprocess.run(['llvm-link', bc_filename, '-o', linked_bc_filename], check=True)
    subprocess.run(['clang++', linked_bc_filename, '-o', output_exe, '-lstdc++', '-lm'], check=True)
    os.remove(obj_filename)
    os.remove(bc_filename)
    os.remove(linked_bc_filename)
    print(f"Executable '{output_exe}' generated.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source_file>")
        sys.exit(1)
    source_file = sys.argv[1]
    base_filename = os.path.splitext(source_file)[0]
    output_exe = base_filename + ".exe"
    with open(source_file, "r") as f:
        source_code = f.read()
    tokens = lex(source_code)
    print(tokens) # for debugging
    parser = Parser(tokens)
    ast = parser.parse()
    codegen = CodeGen()
    codegen.program_node = ast
    llvm_module = codegen.generate_code(ast)
    compile_module(llvm_module, output_exe)
