# codegen.py
import subprocess, os
from llvmlite import binding as llvm
from llvmlite import ir
from ast import *

class CodeGen:
    def __init__(self):
        self.module = ir.Module(name="module")
        self.builder = None
        self.func_symtab = {}
        self.string_counter = 0
        self.program_node = None
        self.class_struct_types = {}
        self.declare_print_func()

        # Operator maps: (int_op, float_op, result_name)
        self.binop_map = {
            '+': ('add', 'fadd', 'addtmp'),
            '-': ('sub', 'fsub', 'subtmp'),
            '*': ('mul', 'fmul', 'multmp'),
            '/': ('sdiv', 'fdiv', 'divtmp'),
            '%': ('srem', 'srem', 'remtmp'),
        }
        # Comparison maps: (int_cmp, float_cmp, result_name)
        self.comp_map = {
            'EQEQ': ('==', '==', 'eqtmp'),
            'NEQ':  ('!=', '!=', 'neqtmp'),
            'LT':   ('<', '<', 'lttmp'),
            'GT':   ('>', '>', 'gttmp'),
            'LTE':  ('<=', '<=', 'letmp'),
            'GTE':  ('>=', '>=', 'getmp'),
        }
        
        # Dispatch table mapping AST node types to handlers.
        # Simple nodes use lambdas; complex ones call dedicated helper methods.
        self.dispatch = {
            Return: lambda n: self.builder.ret(self.codegen(n.expr)),
            ExpressionStatement: lambda n: self.codegen(n.expr),
            Num: lambda n: ir.Constant(ir.IntType(32), n.value),
            FloatNum: lambda n: ir.Constant(ir.FloatType(), n.value),
            String: lambda n: self.create_string_constant(n.value),
            Char: lambda n: ir.Constant(ir.IntType(8), ord(n.value)),
            Var: self.codegen_var,
            BinOp: self.codegen_binop,
            FunctionCall: self.codegen_function_call,
            MemberAccess: self.codegen_member_access,
            Assign: self.codegen_assignment,
            If: self.codegen_if,
            While: self.codegen_while,
            For: self.codegen_for,
            DoWhile: self.codegen_do_while,
            VarDecl: self.codegen_var_decl,
        }

    def declare_print_func(self):
        print_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.print_func = ir.Function(self.module, print_type, name="printf")

    def generate_code(self, node):
        if isinstance(node, Program):
            self.program_node = node
            # First, create class struct types.
            for cls in node.classes:
                self.codegen_class_declaration(cls)
            # Then generate functions.
            for func in node.functions:
                self.codegen_function(func)
        return self.module

    def create_string_constant(self, s):
        s_bytes = bytearray((s + '\0').encode('utf8'))
        str_type = ir.ArrayType(ir.IntType(8), len(s_bytes))
        name = f".str.{self.string_counter}"
        self.string_counter += 1
        global_str = ir.GlobalVariable(self.module, str_type, name=name)
        global_str.global_constant = True
        global_str.linkage = 'private'
        global_str.initializer = ir.Constant(str_type, s_bytes)
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(global_str, [zero, zero], name="str")

    def get_member_index(self, class_name, member_name):
        for cls in self.program_node.classes:
            if cls.name == class_name:
                for i, member in enumerate(cls.members):
                    if member.name == member_name:
                        return i
        raise NameError(f"Member '{member_name}' not found in class '{class_name}'.")

    def promote_to_float(self, left, right):
        if left.type != ir.FloatType():
            left = self.builder.sitofp(left, ir.FloatType())
        if right.type != ir.FloatType():
            right = self.builder.sitofp(right, ir.FloatType())
        return left, right

    # Generic arithmetic and comparison routines
    def gen_arith(self, node, int_op, float_op, res_name):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            return getattr(self.builder, float_op)(left, right, name=f"f{res_name}")
        return getattr(self.builder, int_op)(left, right, name=res_name)

    def gen_compare(self, node, int_cmp, float_cmp, res_name):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            cmp_res = self.builder.fcmp_ordered(float_cmp, left, right, name=f"f{res_name}")
        else:
            cmp_res = self.builder.icmp_signed(int_cmp, left, right, name=res_name)
        return self.builder.zext(cmp_res, ir.IntType(32), name=f"{res_name}_int")

    # Central dispatcher: lookup and call handler from the dispatch map.
    def codegen(self, node):
        for ast_type, handler in self.dispatch.items():
            if isinstance(node, ast_type):
                return handler(node)
        raise NotImplementedError(f"Codegen not implemented for {type(node)}")

    # --- Helper methods for more complex nodes ---

    def codegen_var_decl(self, node):
        basic_types = {
            'int': ir.IntType(32),
            'float': ir.FloatType(),
            'char': ir.IntType(8),
            'string': ir.PointerType(ir.IntType(8))
        }
        if node.datatype_name in basic_types:
            var_type = basic_types[node.datatype_name]
        elif node.datatype_name in self.class_struct_types:
            var_type = ir.PointerType(self.class_struct_types[node.datatype_name])
        else:
            raise ValueError(f"Unknown datatype: {node.datatype_name}")
        addr = self.builder.alloca(var_type, name=node.name)
        if node.init:
            self.builder.store(self.codegen(node.init), addr)
        self.func_symtab[node.name] = {'addr': addr, 'datatype_name': node.datatype_name}
        return addr

    def codegen_binop(self, node):
        if node.op in self.binop_map:
            int_op, float_op, res_name = self.binop_map[node.op]
            return self.gen_arith(node, int_op, float_op, res_name)
        elif node.op in self.comp_map:
            int_cmp, float_cmp, res_name = self.comp_map[node.op]
            return self.gen_compare(node, int_cmp, float_cmp, res_name)
        raise ValueError(f"Unknown binary operator {node.op}")

    def codegen_var(self, node):
        info = self.func_symtab.get(node.name)
        if info:
            return self.builder.load(info['addr'], name=node.name)
        raise NameError(f"Undefined variable: {node.name}")

    def codegen_function_call(self, node):
        if node.name == "print":
            return self.codegen_print_call(node)
        raise NameError(f"Unknown function: {node.name}")

    def codegen_print_call(self, node):
        fmt_parts, llvm_args = [], []
        for arg in node.args:
            val = self.codegen(arg)
            if val.type == ir.FloatType():
                val = self.builder.fpext(val, ir.DoubleType(), name="promoted")
                fmt_parts.append("%f")
            elif val.type == ir.IntType(32):
                fmt_parts.append("%d")
            elif val.type == ir.IntType(8):
                fmt_parts.append("%c")
            elif val.type.is_pointer and val.type.pointee == ir.IntType(8):
                fmt_parts.append("%s")
            else:
                fmt_parts.append("%?")
            llvm_args.append(val)
        fmt_str = " ".join(fmt_parts) + "\n"
        llvm_fmt = self.create_string_constant(fmt_str)
        return self.builder.call(self.print_func, [llvm_fmt] + llvm_args)

    def codegen_member_access(self, node):
        obj_info = self.func_symtab[node.object_expr.name]
        idx = self.get_member_index(obj_info['datatype_name'], node.member_name)
        ptr = self.builder.gep(
            self.builder.load(obj_info['addr']),
            [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)],
            name="member_ptr"
        )
        return self.builder.load(ptr, name=node.member_name)

    def codegen_assignment(self, node):
        if isinstance(node.left, Var):
            info = self.func_symtab.get(node.left.name)
            if not info:
                raise NameError(f"Variable '{node.left.name}' not declared.")
            val = self.codegen(node.right)
            self.builder.store(val, info['addr'])
            return val
        elif isinstance(node.left, MemberAccess):
            return self.codegen_member_assignment(node.left, self.codegen(node.right))
        raise SyntaxError("Invalid left-hand side for assignment")

    def codegen_member_assignment(self, member_node, val):
        obj_info = self.func_symtab[member_node.object_expr.name]
        idx = self.get_member_index(obj_info['datatype_name'], member_node.member_name)
        ptr = self.builder.gep(
            self.builder.load(obj_info['addr']),
            [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)],
            name="member_ptr"
        )
        self.builder.store(val, ptr)
        return val

    def codegen_if(self, node):
        cond = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond, ir.Constant(cond.type, 0), name="ifcond")
        then_bb = self.builder.append_basic_block("then")
        else_bb = self.builder.append_basic_block("else") if node.else_branch else None
        merge_bb = self.builder.append_basic_block("ifcont")
        self.builder.cbranch(cond_bool, then_bb, else_bb if else_bb else merge_bb)
        self.builder.position_at_start(then_bb)
        for stmt in node.then_branch:
            self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.branch(merge_bb)
        if node.else_branch:
            self.builder.position_at_start(else_bb)
            for stmt in node.else_branch:
                self.codegen(stmt)
            if not self.builder.block.terminator:
                self.builder.branch(merge_bb)
        self.builder.position_at_start(merge_bb)
        return ir.Constant(ir.IntType(32), 0)

    def codegen_while(self, node):
        loop_bb = self.builder.append_basic_block("loop")
        after_bb = self.builder.append_basic_block("afterloop")
        self.builder.branch(loop_bb)
        self.builder.position_at_start(loop_bb)
        cond = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond, ir.Constant(cond.type, 0), name="whilecond")
        body_bb = self.builder.append_basic_block("whilebody")
        self.builder.cbranch(cond_bool, body_bb, after_bb)
        self.builder.position_at_start(body_bb)
        for stmt in node.body:
            self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.branch(loop_bb)
        self.builder.position_at_start(after_bb)
        return ir.Constant(ir.IntType(32), 0)

    def codegen_for(self, node):
        self.codegen(node.init)
        loop_bb = self.builder.append_basic_block("forloop")
        after_bb = self.builder.append_basic_block("afterfor")
        self.builder.branch(loop_bb)
        self.builder.position_at_start(loop_bb)
        cond = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond, ir.Constant(cond.type, 0), name="forcond")
        body_bb = self.builder.append_basic_block("forbody")
        self.builder.cbranch(cond_bool, body_bb, after_bb)
        self.builder.position_at_start(body_bb)
        for stmt in node.body:
            self.codegen(stmt)
        self.codegen(node.increment)
        self.builder.branch(loop_bb)
        self.builder.position_at_start(after_bb)
        return ir.Constant(ir.IntType(32), 0)

    def codegen_do_while(self, node):
        loop_bb = self.builder.append_basic_block("dowhileloop")
        after_bb = self.builder.append_basic_block("afterdowhile")
        self.builder.branch(loop_bb)
        self.builder.position_at_start(loop_bb)
        for stmt in node.body:
            self.codegen(stmt)
        cond = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond, ir.Constant(cond.type, 0), name="dowhilecond")
        self.builder.cbranch(cond_bool, loop_bb, after_bb)
        self.builder.position_at_start(after_bb)
        return ir.Constant(ir.IntType(32), 0)

    def codegen_class_declaration(self, node):
        # Build a struct type for the class (here assuming all members are int32).
        members = [ir.IntType(32) for _ in node.members]
        self.class_struct_types[node.name] = ir.LiteralStructType(members)

    def codegen_function(self, node):
        func_type = ir.FunctionType(ir.IntType(32), [])
        func = ir.Function(self.module, func_type, name=node.name)
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.func_symtab = {}
        retval = None
        for stmt in node.body:
            retval = self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.ret(retval if retval else ir.Constant(ir.IntType(32), 0))
