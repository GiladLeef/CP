# codegen.py
import subprocess
import os
from llvmlite import binding as llvm
from llvmlite import ir
from ast import *

class CodeGen:
    def __init__(self):
        self.module = ir.Module(name="my_module")
        self.builder = None
        self.func_symtab = {}
        self.string_counter = 0
        self.declare_print_func()
        self.program_node = None
        self.class_struct_types = {}
        self.node_codegen_map = {
            Return: self.codegen_return,
            ExpressionStatement: self.codegen_expression_statement,
            VarDecl: self.codegen_var_decl,
            BinOp: self.codegen_binop,
            Num: self.codegen_num,
            FloatNum: self.codegen_floatnum,
            String: self.codegen_string,
            Char: self.codegen_char,
            Var: self.codegen_var,
            FunctionCall: self.codegen_function_call,
            MemberAccess: self.codegen_member_access,
            Assign: self.codegen_assignment,
            If: self.codegen_if,
            While: self.codegen_while,
            For: self.codegen_for,
            DoWhile: self.codegen_do_while,
        }
        self.binop_codegen_map = {
            '+': self.codegen_add,
            '-': self.codegen_sub,
            '*': self.codegen_mul,
            '/': self.codegen_div,
            '%': self.codegen_rem,
            'EQEQ': self.codegen_eqeq,
            'NEQ': self.codegen_neq,
            'LT': self.codegen_lt,
            'GT': self.codegen_gt,
            'LTE': self.codegen_lte,
            'GTE': self.codegen_gte,
        }
    def declare_print_func(self):
        print_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
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
        for member_decl in node.members:
            member_types.append(ir.IntType(32))
        class_struct_type = ir.LiteralStructType(member_types)
        self.class_struct_types[class_name] = class_struct_type
    def codegen(self, node):
        node_type = type(node)
        if node_type in self.node_codegen_map:
            return self.node_codegen_map[node_type](node)
        raise NotImplementedError(f"Codegen not implemented for {node_type}")
    def codegen_return(self, node):
        ret_val = self.codegen(node.expr)
        self.builder.ret(ret_val)
        return ret_val
    def codegen_expression_statement(self, node):
        return self.codegen(node.expr)
    def codegen_var_decl(self, node):
        var_type = None
        if node.datatype_name == 'int':
            var_type = ir.IntType(32)
        elif node.datatype_name == 'float':
            var_type = ir.FloatType()
        elif node.datatype_name == 'char':
            var_type = ir.IntType(8)
        elif node.datatype_name == 'string':
            var_type = ir.PointerType(ir.IntType(8))
        elif node.datatype_name in self.class_struct_types:
            var_type = ir.PointerType(self.class_struct_types[node.datatype_name])
        else:
            raise ValueError(f"Unknown datatype: {node.datatype_name}")
        var_addr = self.builder.alloca(var_type, name=node.name)
        if node.init:
            init_val = self.codegen(node.init)
            self.builder.store(init_val, var_addr)
        self.func_symtab[node.name] = {'addr': var_addr, 'datatype_name': node.datatype_name}
        return var_addr
    def codegen_binop(self, node):
        if node.op in self.binop_codegen_map:
            return self.binop_codegen_map[node.op](node)
        raise ValueError(f"Unknown binary operator {node.op}")
    def codegen_add(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            return self.builder.fadd(left, right, name="faddtmp")
        return self.builder.add(left, right, name="addtmp")
    def codegen_sub(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            return self.builder.fsub(left, right, name="fsubtmp")
        return self.builder.sub(left, right, name="subtmp")
    def codegen_mul(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            return self.builder.fmul(left, right, name="fmultmp")
        return self.builder.mul(left, right, name="multmp")
    def codegen_div(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            return self.builder.fdiv(left, right, name="fdivtmp")
        return self.builder.sdiv(left, right, name="divtmp")
    def codegen_rem(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        return self.builder.srem(left, right, name="remtmp")
    def codegen_eqeq(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            bool_val = self.builder.fcmp_ordered("==", left, right, name="feqtmp")
        else:
            bool_val = self.builder.icmp_signed("==", left, right, name="eqtmp")
        return self.builder.zext(bool_val, ir.IntType(32), name="eq_int_tmp")
    def codegen_neq(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            bool_val = self.builder.fcmp_ordered("!=", left, right, name="fneqtmp")
        else:
            bool_val = self.builder.icmp_signed("!=", left, right, name="neqtmp")
        return self.builder.zext(bool_val, ir.IntType(32), name="neq_int_tmp")
    def codegen_lt(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            bool_val = self.builder.fcmp_ordered("<", left, right, name="flttmp")
        else:
            bool_val = self.builder.icmp_signed("<", left, right, name="lttmp")
        return self.builder.zext(bool_val, ir.IntType(32), name="lt_int_tmp")
    def codegen_gt(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            bool_val = self.builder.fcmp_ordered(">", left, right, name="fgttmp")
        else:
            bool_val = self.builder.icmp_signed(">", left, right, name="gttmp")
        return self.builder.zext(bool_val, ir.IntType(32), name="gt_int_tmp")
    def codegen_lte(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            bool_val = self.builder.fcmp_ordered("<=", left, right, name="fletmp")
        else:
            bool_val = self.builder.icmp_signed("<=", left, right, name="letmp")
        return self.builder.zext(bool_val, ir.IntType(32), name="lte_int_tmp")
    def codegen_gte(self, node):
        left, right = self.codegen(node.left), self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promote_to_float(left, right)
            bool_val = self.builder.fcmp_ordered(">=", left, right, name="fgetmp")
        else:
            bool_val = self.builder.icmp_signed(">=", left, right, name="getmp")
        return self.builder.zext(bool_val, ir.IntType(32), name="gte_int_tmp")
    def promote_to_float(self, left, right):
        if left.type != ir.FloatType():
            left = self.builder.sitofp(left, ir.FloatType())
        if right.type != ir.FloatType():
            right = self.builder.sitofp(right, ir.FloatType())
        return left, right
    def codegen_num(self, node):
        return ir.Constant(ir.IntType(32), node.value)
    def codegen_floatnum(self, node):
        return ir.Constant(ir.FloatType(), node.value)
    def codegen_string(self, node):
        return self.create_string_constant(node.value)
    def codegen_char(self, node):
        return ir.Constant(ir.IntType(8), ord(node.value))
    def codegen_var(self, node):
        if node.name in self.func_symtab:
            var_info = self.func_symtab[node.name]
            var_addr = var_info['addr']
            return self.builder.load(var_addr, name=node.name)
        raise NameError(f"Undefined variable: {node.name}")
    def codegen_function_call(self, node):
        if node.name == "print":
            return self.codegen_print_call(node)
        raise NameError(f"Unknown function: {node.name}")
    def codegen_member_access(self, node):
        object_name = node.object_expr.name
        member_name = node.member_name
        var_info = self.func_symtab[object_name]
        class_name = var_info['datatype_name']
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
        return self.builder.load(ptr, name=member_name)
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
        raise SyntaxError("Invalid left-hand side for assignment")
    def codegen_if(self, node):
        cond_val = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0), name="ifcond")
        then_bb = self.builder.append_basic_block("then")
        else_bb = self.builder.append_basic_block("else") if node.else_branch is not None else None
        merge_bb = self.builder.append_basic_block("ifcont")
        if else_bb:
            self.builder.cbranch(cond_bool, then_bb, else_bb)
        else:
            self.builder.cbranch(cond_bool, then_bb, merge_bb)
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
        cond_val = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0), name="whilecond")
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
        cond_val = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0), name="forcond")
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
        cond_val = self.codegen(node.condition)
        cond_bool = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0), name="dowhilecond")
        self.builder.cbranch(cond_bool, loop_bb, after_bb)
        self.builder.position_at_start(after_bb)
        return ir.Constant(ir.IntType(32), 0)
    def codegen_member_assignment(self, member_access_node, assign_val):
        object_name = member_access_node.object_expr.name
        var_info = self.func_symtab[object_name]
        class_name = var_info['datatype_name']
        member_index = -1
        class_decl_node = None
        for program_node in self.program_node.functions + self.program_node.classes:
            if isinstance(program_node, ClassDecl) and program_node.name == class_name:
                class_decl_node = program_node
                break
        if class_decl_node:
            for i, member in enumerate(class_decl_node.members):
                if member.name == member_access_node.member_name:
                    member_index = i
                    break
        if member_index == -1:
            raise NameError(f"Member '{member_access_node.member_name}' not found in class '{class_name}'.")
        object_addr = var_info['addr']
        ptr = self.builder.gep(self.builder.load(object_addr), [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), member_index)], name="member_ptr")
        self.builder.store(assign_val, ptr)
        return assign_val
    def codegen_print_call(self, node):
        format_str_parts = []
        llvm_args = []
        for arg_node in node.args:
            arg_val = self.codegen(arg_node)
            if arg_val.type == ir.FloatType():
                arg_val = self.builder.fpext(arg_val, ir.DoubleType(), name="promoted")
                format_str_parts.append("%f")
            elif arg_val.type == ir.IntType(32):
                format_str_parts.append("%d")
            elif arg_val.type == ir.IntType(8):
                format_str_parts.append("%c")
            elif arg_val.type.is_pointer and arg_val.type.pointee == ir.IntType(8):
                format_str_parts.append("%s")
            else:
                format_str_parts.append("%?")
            llvm_args.append(arg_val)
        full_format_str = " ".join(format_str_parts) + "\n"
        llvm_format_str = self.create_string_constant(full_format_str)
        print_args = [llvm_format_str] + llvm_args
        return self.builder.call(self.print_func, print_args)
