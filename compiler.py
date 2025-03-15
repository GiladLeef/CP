import json
import subprocess
import os
import re
import sys
from llvmlite import binding as llvm
from llvmlite import ir

class ASTFactory:
    def __init__(self, lang_def):
        self.lang_def = lang_def
        self.ast_classes = {}
        self.create_ast_classes()
    def create_ast_classes(self):
        for node in self.lang_def["astNodes"]:
            self.ast_classes[node["name"]] = self.create_ast_class(node["name"], node["fields"])
    def create_ast_class(self, name, fields):
        def __init__(self, *args):
            if len(args) != len(fields):
                raise TypeError("Expected %d args" % len(fields))
            for f, a in zip(fields, args):
                setattr(self, f, a)
        def __repr__(self):
            return name + "(" + ", ".join(str(getattr(self, f)) for f in fields) + ")"
        return type(name, (object,), {"__init__": __init__, "__repr__": __repr__})

class Token:
    def __init__(self, token_type, token_value):
        self.token_type = token_type
        self.token_value = token_value
    def __repr__(self):
        return "Token(%s, %s)" % (self.token_type, self.token_value)

class Lexer:
    def __init__(self, tokens):
        self.tokens = tokens
    def lex(self, characters):
        curr_pos = 0
        token_list = []
        while curr_pos < len(characters):
            match_found = None
            for token_type, pattern in self.tokens:
                regex = re.compile(pattern)
                match_found = regex.match(characters, curr_pos)
                if match_found:
                    text = match_found.group(0)
                    if token_type == "COMMENT":
                        curr_pos = match_found.end(0)
                        break
                    if token_type != "WS":
                        if token_type == "STRING":
                            text = text[1:-1]
                        elif token_type == "CHAR_LITERAL":
                            text = text[1:-1]
                        token_list.append(Token(token_type, text))
                    curr_pos = match_found.end(0)
                    break
            if not match_found:
                raise SyntaxError("Illegal character: " + characters[curr_pos])
        return token_list

class Parser:
    def __init__(self, tokens, ast_classes):
        self.tokens = tokens
        self.pos = 0
        self.ast_classes = ast_classes
        self.class_names = set()
        self.statement_parse_map = {
            "RETURN": self.parseReturn,
            "IF": self.parseIf,
            "WHILE": self.parseWhile,
            "FOR": self.parseFor,
            "DO": self.parseDoWhile
        }
        self.factor_parse_map = {
            "NUMBER": lambda: self.parseLiteral("NUMBER", "Num"),
            "FLOAT_NUMBER": lambda: self.parseLiteral("FLOAT_NUMBER", "FloatNum"),
            "STRING": lambda: self.parseLiteral("STRING", "String"),
            "CHAR_LITERAL": lambda: self.parseLiteral("CHAR_LITERAL", "Char"),
            "ID": self.parseIdentifier,
            "LPAREN": self.parseParenthesizedExpression
        }
    def currentToken(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    def consumeToken(self, token_type):
        token = self.currentToken()
        if token and token.token_type == token_type:
            self.pos += 1
            return token
        raise SyntaxError("Expected token " + token_type + ", got " + str(token))
    def parseLiteral(self, token_type, ast_name):
        token = self.consumeToken(token_type)
        return self.ast_classes[ast_name](token.token_value)
    def parseProgram(self):
        functions = []
        classes = []
        while self.currentToken() is not None:
            if self.currentToken().token_type == "CLASS":
                class_decl = self.parseClassDeclaration()
                classes.append(class_decl)
                self.class_names.add(class_decl.name)
            elif self.currentToken().token_type in ("INT", "FLOAT", "CHAR", "ID") and (self.currentToken().token_type != "ID" or self.currentToken().token_value != "class"):
                functions.append(self.parseFunction())
            else:
                self.consumeToken(self.currentToken().token_type)
        return self.ast_classes["Program"](functions, classes)
    def parseClassDeclaration(self):
        self.consumeToken("CLASS")
        class_name = self.consumeToken("ID").token_value
        self.consumeToken("LBRACE")
        members = []
        while self.currentToken() and self.currentToken().token_type != "RBRACE":
            member = self.parseDeclarationMember()
            if type(member).__name__ != "VarDecl":
                raise SyntaxError("Class members must be variable declarations")
            members.append(member)
        self.consumeToken("RBRACE")
        return self.ast_classes["ClassDecl"](class_name, members)
    def parseDeclarationMember(self):
        data_type_token = self.consumeDatatype()
        var_name = self.consumeToken("ID").token_value
        self.consumeToken("SEMICOLON")
        return self.ast_classes["VarDecl"](var_name, None, data_type_token.token_value)
    def parseDeclaration(self):
        data_type_token = self.consumeDatatype()
        var_name = self.consumeToken("ID").token_value
        data_type_name = data_type_token.token_value
        if self.currentToken() and self.currentToken().token_type == "EQ":
            self.consumeToken("EQ")
            init_expr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.ast_classes["VarDecl"](var_name, init_expr, data_type_name)
        self.consumeToken("SEMICOLON")
        return self.ast_classes["VarDecl"](var_name, None, data_type_name)
    def parseFunction(self):
        data_type_token = self.consumeDatatype()
        name = self.consumeToken("ID").token_value
        self.consumeToken("LPAREN")
        self.consumeToken("RPAREN")
        self.consumeToken("LBRACE")
        body = []
        while self.currentToken() and self.currentToken().token_type != "RBRACE":
            body.append(self.parseStatement())
        self.consumeToken("RBRACE")
        return self.ast_classes["Function"](name, body)
    def parseStatement(self):
        token = self.currentToken()
        if token.token_type in self.statement_parse_map:
            return self.statement_parse_map[token.token_type]()
        elif token.token_type in ("INT", "FLOAT", "CHAR") or (token.token_type == "ID" and token.token_value == "string"):
            return self.parseDeclaration()
        else:
            expr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.ast_classes["ExpressionStatement"](expr)
    def consumeDatatype(self):
        token = self.currentToken()
        if token.token_type in ("INT", "FLOAT", "CHAR") or (token.token_type == "ID" and (token.token_value in self.class_names or token.token_value == "string")):
            self.pos += 1
            return token
        raise SyntaxError("Expected datatype, got " + str(token))
    def parseReturn(self):
        self.consumeToken("RETURN")
        expr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.ast_classes["Return"](expr)
    def parseExpression(self):
        node = self.parseAssignment()
        return node
    def parseAssignment(self):
        node = self.parseComparison()
        if self.currentToken() and self.currentToken().token_type == "EQ":
            self.consumeToken("EQ")
            right = self.parseAssignment()
            if node.__class__.__name__ in ("MemberAccess", "Var"):
                return self.ast_classes["Assign"](node, right)
            raise SyntaxError("Invalid left-hand side for assignment")
        return node
    def parseComparison(self):
        node = self.parseAdditiveExpression()
        while self.currentToken() and self.currentToken().token_type in ("EQEQ", "NEQ", "LT", "GT", "LTE", "GTE"):
            op_token = self.consumeToken(self.currentToken().token_type)
            op = op_token.token_type
            right = self.parseAdditiveExpression()
            node = self.ast_classes["BinOp"](op, node, right)
        return node
    def parseAdditiveExpression(self):
        node = self.parseMultiplicativeExpression()
        while self.currentToken() and self.currentToken().token_type in ("PLUS", "MINUS"):
            op = self.consumeToken(self.currentToken().token_type).token_value
            right = self.parseMultiplicativeExpression()
            node = self.ast_classes["BinOp"](op, node, right)
        return node
    def parseMultiplicativeExpression(self):
        node = self.parseFactor()
        while self.currentToken() and self.currentToken().token_type in ("MULT", "DIV", "MOD"):
            op = self.consumeToken(self.currentToken().token_type).token_value
            right = self.parseFactor()
            node = self.ast_classes["BinOp"](op, node, right)
        return node
    def parseFactor(self):
        token = self.currentToken()
        if token.token_type in self.factor_parse_map:
            return self.factor_parse_map[token.token_type]()
        raise SyntaxError("Unexpected token: " + str(token))
    def parseIdentifier(self):
        token = self.consumeToken("ID")
        name = token.token_value
        if self.currentToken() and self.currentToken().token_type == "DOT":
            self.consumeToken("DOT")
            member_name = self.consumeToken("ID").token_value
            return self.ast_classes["MemberAccess"](self.ast_classes["Var"](name), member_name)
        elif self.currentToken() and self.currentToken().token_type == "LPAREN":
            return self.parseFunctionCall(name)
        return self.ast_classes["Var"](name)
    def parseParenthesizedExpression(self):
        self.consumeToken("LPAREN")
        node = self.parseExpression()
        self.consumeToken("RPAREN")
        return node
    def parseFunctionCall(self, name):
        self.consumeToken("LPAREN")
        args = []
        if self.currentToken() and self.currentToken().token_type != "RPAREN":
            args.append(self.parseExpression())
            while self.currentToken() and self.currentToken().token_type == "COMMA":
                self.consumeToken("COMMA")
                args.append(self.parseExpression())
        self.consumeToken("RPAREN")
        return self.ast_classes["FunctionCall"](name, args)
    def parseIf(self):
        self.consumeToken("IF")
        if self.currentToken().token_type == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        then_branch = self.parseBlock()
        else_branch = None
        if self.currentToken() and self.currentToken().token_type == "ELSE":
            self.consumeToken("ELSE")
            if self.currentToken() and self.currentToken().token_type == "IF":
                else_branch = [self.parseIf()]
            else:
                else_branch = self.parseBlock()
        return self.ast_classes["If"](condition, then_branch, else_branch)
    def parseWhile(self):
        self.consumeToken("WHILE")
        if self.currentToken().token_type == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        body = self.parseBlock()
        return self.ast_classes["While"](condition, body)
    def parseFor(self):
        self.consumeToken("FOR")
        self.consumeToken("LPAREN")
        init = self.parseStatement()
        condition = self.parseExpression()
        self.consumeToken("SEMICOLON")
        increment = self.parseExpression()
        self.consumeToken("RPAREN")
        body = self.parseBlock()
        return self.ast_classes["For"](init, condition, increment, body)
    def parseDoWhile(self):
        self.consumeToken("DO")
        body = self.parseBlock()
        self.consumeToken("WHILE")
        if self.currentToken().token_type == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.ast_classes["DoWhile"](body, condition)
    def parseBlock(self):
        self.consumeToken("LBRACE")
        stmts = []
        while self.currentToken() and self.currentToken().token_type != "RBRACE":
            stmts.append(self.parseStatement())
        self.consumeToken("RBRACE")
        return stmts

class CodeGen:
    def __init__(self, lang_def):
        self.module = ir.Module(name="module")
        self.builder = None
        self.funcSymtab = {}
        self.stringCounter = 0
        self.programNode = None
        self.classStructTypes = {}
        self.declarePrintFunc()
        self.binOpMap = lang_def["operators"]["binOpMap"]
        self.compMap = lang_def["operators"]["compMap"]
        self.dispatch = {
            "Return": lambda n: self.builder.ret(self.codegen(n.expr)),
            "ExpressionStatement": lambda n: self.codegen(n.expr),
            "Num": lambda n: ir.Constant(ir.IntType(32), n.value),
            "FloatNum": lambda n: ir.Constant(ir.FloatType(), float(n.value)),
            "String": lambda n: self.createStringConstant(n.value),
            "Char": lambda n: ir.Constant(ir.IntType(8), ord(n.value)),
            "Var": self.codegenVar,
            "BinOp": self.codegenBinop,
            "FunctionCall": self.codegenFunctionCall,
            "MemberAccess": self.codegenMemberAccess,
            "Assign": self.codegenAssignment,
            "If": self.codegenIf,
            "While": self.codegenWhile,
            "For": self.codegenFor,
            "DoWhile": self.codegenDoWhile,
            "VarDecl": self.codegenVarDecl
        }
    def declarePrintFunc(self):
        printType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.printFunc = ir.Function(self.module, printType, name="printf")
    def generateCode(self, node):
        if node.__class__.__name__ == "Program":
            self.programNode = node
            for cls in node.classes:
                self.codegenClassDeclaration(cls)
            for func in node.functions:
                self.codegenFunction(func)
        return self.module
    def createStringConstant(self, s):
        sBytes = bytearray((s + "\0").encode("utf8"))
        strType = ir.ArrayType(ir.IntType(8), len(sBytes))
        name = ".str." + str(self.stringCounter)
        self.stringCounter += 1
        globalStr = ir.GlobalVariable(self.module, strType, name=name)
        globalStr.global_constant = True
        globalStr.linkage = "private"
        globalStr.initializer = ir.Constant(strType, sBytes)
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(globalStr, [zero, zero], name="str")
    def getMemberIndex(self, className, memberName):
        for cls in self.programNode.classes:
            if cls.name == className:
                for i, member in enumerate(cls.members):
                    if member.name == memberName:
                        return i
        raise NameError("Member '" + memberName + "' not found in class '" + className + "'.")
    def promoteToFloat(self, left, right):
        if left.type != ir.FloatType():
            left = self.builder.sitofp(left, ir.FloatType())
        if right.type != ir.FloatType():
            right = self.builder.sitofp(right, ir.FloatType())
        return left, right
    def genArith(self, node, intOp, floatOp, resName):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promoteToFloat(left, right)
            return getattr(self.builder, floatOp)(left, right, name="f" + resName)
        return getattr(self.builder, intOp)(left, right, name=resName)
    def genCompare(self, node, intCmp, floatCmp, resName):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        if left.type == ir.FloatType() or right.type == ir.FloatType():
            left, right = self.promoteToFloat(left, right)
            cmpRes = self.builder.fcmp_ordered(floatCmp, left, right, name="f" + resName)
        else:
            cmpRes = self.builder.icmp_signed(intCmp, left, right, name=resName)
        return self.builder.zext(cmpRes, ir.IntType(32), name=resName + "Int")
    def codegen(self, node):
        nodeType = node.__class__.__name__
        if nodeType in self.dispatch:
            return self.dispatch[nodeType](node)
        raise NotImplementedError("Codegen not implemented for " + nodeType)
    def codegenVarDecl(self, node):
        basicTypes = {"int": ir.IntType(32), "float": ir.FloatType(), "char": ir.IntType(8), "string": ir.PointerType(ir.IntType(8))}
        if node.datatypeName in basicTypes:
            varType = basicTypes[node.datatypeName]
        elif node.datatypeName in self.classStructTypes:
            varType = ir.PointerType(self.classStructTypes[node.datatypeName])
        else:
            raise ValueError("Unknown datatype: " + node.datatypeName)
        addr = self.builder.alloca(varType, name=node.name)
        if node.init:
            self.builder.store(self.codegen(node.init), addr)
        self.funcSymtab[node.name] = {"addr": addr, "datatypeName": node.datatypeName}
        return addr
    def codegenBinop(self, node):
        if node.op in self.binOpMap:
            intOp, floatOp, resName = self.binOpMap[node.op]
            return self.genArith(node, intOp, floatOp, resName)
        elif node.op in self.compMap:
            intCmp, floatCmp, resName = self.compMap[node.op]
            return self.genCompare(node, intCmp, floatCmp, resName)
        raise ValueError("Unknown binary operator " + node.op)
    def codegenVar(self, node):
        info = self.funcSymtab.get(node.name)
        if info:
            return self.builder.load(info["addr"], name=node.name)
        raise NameError("Undefined variable: " + node.name)
    def codegenFunctionCall(self, node):
        if node.name == "print":
            return self.codegenPrintCall(node)
        raise NameError("Unknown function: " + node.name)
    def codegenPrintCall(self, node):
        fmtParts = []
        llvmArgs = []
        for arg in node.args:
            val = self.codegen(arg)
            if val.type == ir.FloatType():
                val = self.builder.fpext(val, ir.DoubleType(), name="promoted")
                fmtParts.append("%f")
            elif val.type == ir.IntType(32):
                fmtParts.append("%d")
            elif val.type == ir.IntType(8):
                fmtParts.append("%c")
            elif val.type.is_pointer and val.type.pointee == ir.IntType(8):
                fmtParts.append("%s")
            else:
                fmtParts.append("%?")
            llvmArgs.append(val)
        fmtStr = " ".join(fmtParts) + "\n"
        llvmFmt = self.createStringConstant(fmtStr)
        return self.builder.call(self.printFunc, [llvmFmt] + llvmArgs)
    def codegenMemberAccess(self, node):
        objInfo = self.funcSymtab[node.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], node.memberName)
        ptr = self.builder.gep(self.builder.load(objInfo["addr"]), [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name="memberPtr")
        return self.builder.load(ptr, name=node.memberName)
    def codegenAssignment(self, node):
        if node.left.__class__.__name__ == "Var":
            info = self.funcSymtab.get(node.left.name)
            if not info:
                raise NameError("Variable '" + node.left.name + "' not declared.")
            val = self.codegen(node.right)
            self.builder.store(val, info["addr"])
            return val
        elif node.left.__class__.__name__ == "MemberAccess":
            return self.codegenMemberAssignment(node.left, self.codegen(node.right))
        raise SyntaxError("Invalid left-hand side for assignment")
    def codegenMemberAssignment(self, memberNode, val):
        objInfo = self.funcSymtab[memberNode.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], memberNode.memberName)
        ptr = self.builder.gep(self.builder.load(objInfo["addr"]), [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name="memberPtr")
        self.builder.store(val, ptr)
        return val
    def codegenIf(self, node):
        cond = self.codegen(node.condition)
        condBool = self.builder.icmp_unsigned("!=", cond, ir.Constant(cond.type, 0), name="ifcond")
        thenBb = self.builder.append_basic_block("then")
        elseBb = self.builder.append_basic_block("else") if node.elseBranch else None
        mergeBb = self.builder.append_basic_block("ifcont")
        self.builder.cbranch(condBool, thenBb, elseBb if elseBb else mergeBb)
        self.builder.position_at_start(thenBb)
        for stmt in node.thenBranch:
            self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.branch(mergeBb)
        if node.elseBranch:
            self.builder.position_at_start(elseBb)
            for stmt in node.elseBranch:
                self.codegen(stmt)
            if not self.builder.block.terminator:
                self.builder.branch(mergeBb)
        self.builder.position_at_start(mergeBb)
        return ir.Constant(ir.IntType(32), 0)
    def codegenWhile(self, node):
        loopBb = self.builder.append_basic_block("loop")
        afterBb = self.builder.append_basic_block("afterloop")
        self.builder.branch(loopBb)
        self.builder.position_at_start(loopBb)
        cond = self.codegen(node.condition)
        condBool = self.builder.icmp_unsigned("!=", cond, ir.Constant(cond.type, 0), name="whilecond")
        bodyBb = self.builder.append_basic_block("whilebody")
        self.builder.cbranch(condBool, bodyBb, afterBb)
        self.builder.position_at_start(bodyBb)
        for stmt in node.body:
            self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.branch(loopBb)
        self.builder.position_at_start(afterBb)
        return ir.Constant(ir.IntType(32), 0)
    def codegenFor(self, node):
        self.codegen(node.init)
        loopBb = self.builder.append_basic_block("forloop")
        afterBb = self.builder.append_basic_block("afterfor")
        self.builder.branch(loopBb)
        self.builder.position_at_start(loopBb)
        cond = self.codegen(node.condition)
        condBool = self.builder.icmp_unsigned("!=", cond, ir.Constant(cond.type, 0), name="forcond")
        bodyBb = self.builder.append_basic_block("forbody")
        self.builder.cbranch(condBool, bodyBb, afterBb)
        self.builder.position_at_start(bodyBb)
        for stmt in node.body:
            self.codegen(stmt)
        self.codegen(node.increment)
        self.builder.branch(loopBb)
        self.builder.position_at_start(afterBb)
        return ir.Constant(ir.IntType(32), 0)
    def codegenDoWhile(self, node):
        loopBb = self.builder.append_basic_block("dowhileloop")
        afterBb = self.builder.append_basic_block("afterdowhile")
        self.builder.branch(loopBb)
        self.builder.position_at_start(loopBb)
        for stmt in node.body:
            self.codegen(stmt)
        cond = self.codegen(node.condition)
        condBool = self.builder.icmp_unsigned("!=", cond, ir.Constant(cond.type, 0), name="dowhilecond")
        self.builder.cbranch(condBool, loopBb, afterBb)
        self.builder.position_at_start(afterBb)
        return ir.Constant(ir.IntType(32), 0)
    def codegenClassDeclaration(self, node):
        members = [ir.IntType(32) for _ in node.members]
        self.classStructTypes[node.name] = ir.LiteralStructType(members)
    def codegenFunction(self, node):
        funcType = ir.FunctionType(ir.IntType(32), [])
        func = ir.Function(self.module, funcType, name=node.name)
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.funcSymtab = {}
        retval = None
        for stmt in node.body:
            retval = self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.ret(retval if retval else ir.Constant(ir.IntType(32), 0))

class Compiler:
    def __init__(self, lang_file="lang.json"):
        self.lang_def = json.load(open(lang_file, "r"))
        self.ast_factory = ASTFactory(self.lang_def)
        self.tokens = [(t["type"], t["regex"]) for t in self.lang_def["tokens"]]
        self.lexer = Lexer(self.tokens)
    def compile_source(self, source_code, output_exe):
        tokens = self.lexer.lex(source_code)
        parser = Parser(tokens, self.ast_factory.ast_classes)
        ast = parser.parseProgram()
        codegen = CodeGen(self.lang_def)
        codegen.programNode = ast
        llvm_module = codegen.generateCode(ast)
        self.compile_module(llvm_module, output_exe)
    def compile_module(self, llvm_module, output_exe):
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
        with open(bc_filename, "w") as f:
            f.write(str(llvm_module))
        linked_bc_filename = "linked.bc"
        subprocess.run(["llvm-link", bc_filename, "-o", linked_bc_filename], check=True)
        subprocess.run(["clang++", linked_bc_filename, "-o", output_exe, "-lstdc++", "-lm"], check=True)
        os.remove(obj_filename)
        os.remove(bc_filename)
        os.remove(linked_bc_filename)
        print("Executable '" + output_exe + "' generated.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <sourceFile>")
        sys.exit(1)
    source_file = sys.argv[1]
    base_filename = os.path.splitext(source_file)[0]
    output_exe = base_filename + ".exe"
    with open(source_file, "r") as f:
        source_code = f.read()
    compiler = Compiler()
    compiler.compile_source(source_code, output_exe)
