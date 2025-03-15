import json
import subprocess
import os
import re
import sys
from llvmlite import binding as llvm
from llvmlite import ir

class AstFactory:
    def __init__(self, langDef):
        self.langDef = langDef
        self.astClasses = {}
        self.createAstClasses()
    def createAstClasses(self):
        for node in self.langDef["astNodes"]:
            self.astClasses[node["name"]] = self.createAstClass(node["name"], node["fields"])
    def createAstClass(self, name, fields):
        def init(self, *args):
            if len(args) != len(fields):
                raise TypeError("Expected %d args" % len(fields))
            for f, a in zip(fields, args):
                setattr(self, f, a)
        def repr(self):
            return name + "(" + ", ".join(str(getattr(self, f)) for f in fields) + ")"
        return type(name, (object,), {"__init__": init, "__repr__": repr})

class Token:
    def __init__(self, tokenType, tokenValue):
        self.tokenType = tokenType
        self.tokenValue = tokenValue
    def __repr__(self):
        return "Token(%s, %s)" % (self.tokenType, self.tokenValue)

class Lexer:
    def __init__(self, tokens):
        self.tokens = [(tokenType, re.compile(pattern)) for tokenType, pattern in tokens]
    def lex(self, characters):
        currPos = 0
        tokenList = []
        while currPos < len(characters):
            matchFound = None
            for tokenType, regex in self.tokens:
                matchFound = regex.match(characters, currPos)
                if matchFound:
                    text = matchFound.group(0)
                    if tokenType == "COMMENT":
                        currPos = matchFound.end(0)
                        break
                    if tokenType != "WS":
                        if tokenType == "STRING" or tokenType == "CHAR_LITERAL":
                            text = text[1:-1]
                        tokenList.append(Token(tokenType, text))
                    currPos = matchFound.end(0)
                    break
            if not matchFound:
                raise SyntaxError("Illegal character: " + characters[currPos])
        return tokenList

class Parser:
    def __init__(self, tokens, astClasses):
        self.tokens = tokens
        self.pos = 0
        self.astClasses = astClasses
        self.classNames = set()
        self.statementParseMap = {
            "RETURN": self.parseReturn,
            "IF": self.parseIf,
            "WHILE": self.parseWhile,
            "FOR": self.parseFor,
            "DO": self.parseDoWhile
        }
        self.factorParseMap = {
            "NUMBER": lambda: self.parseLiteral("NUMBER", "Num"),
            "FLOAT_NUMBER": lambda: self.parseLiteral("FLOAT_NUMBER", "FloatNum"),
            "STRING": lambda: self.parseLiteral("STRING", "String"),
            "CHAR_LITERAL": lambda: self.parseLiteral("CHAR_LITERAL", "Char"),
            "ID": self.parseIdentifier,
            "LPAREN": self.parseParenthesizedExpression
        }
    def currentToken(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    def consumeToken(self, tokenType):
        token = self.currentToken()
        if token and token.tokenType == tokenType:
            self.pos += 1
            return token
        raise SyntaxError("Expected token " + tokenType + ", got " + str(token))
    def parseLiteral(self, tokenType, astName):
        token = self.consumeToken(tokenType)
        return self.astClasses[astName](token.tokenValue)
    def parseProgram(self):
        functions = []
        classes = []
        while self.currentToken() is not None:
            if self.currentToken().tokenType == "CLASS":
                classDecl = self.parseClassDeclaration()
                classes.append(classDecl)
                self.classNames.add(classDecl.name)
            elif self.currentToken().tokenType in ("INT", "FLOAT", "CHAR", "ID") and (self.currentToken().tokenType != "ID" or self.currentToken().tokenValue != "class"):
                functions.append(self.parseFunction())
            else:
                self.consumeToken(self.currentToken().tokenType)
        return self.astClasses["Program"](functions, classes)
    def parseClassDeclaration(self):
        self.consumeToken("CLASS")
        className = self.consumeToken("ID").tokenValue
        self.consumeToken("LBRACE")
        members = []
        while self.currentToken() and self.currentToken().tokenType != "RBRACE":
            member = self.parseDeclarationMember()
            if type(member).__name__ != "VarDecl":
                raise SyntaxError("Class members must be variable declarations")
            members.append(member)
        self.consumeToken("RBRACE")
        return self.astClasses["ClassDecl"](className, members)
    def parseDeclarationMember(self):
        dataTypeToken = self.consumeDatatype()
        varName = self.consumeToken("ID").tokenValue
        self.consumeToken("SEMICOLON")
        return self.astClasses["VarDecl"](varName, None, dataTypeToken.tokenValue)
    def parseDeclaration(self):
        dataTypeToken = self.consumeDatatype()
        varName = self.consumeToken("ID").tokenValue
        dataTypeName = dataTypeToken.tokenValue
        if self.currentToken() and self.currentToken().tokenType == "EQ":
            self.consumeToken("EQ")
            initExpr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.astClasses["VarDecl"](varName, initExpr, dataTypeName)
        self.consumeToken("SEMICOLON")
        return self.astClasses["VarDecl"](varName, None, dataTypeName)
    def parseFunction(self):
        dataTypeToken = self.consumeDatatype()
        name = self.consumeToken("ID").tokenValue
        self.consumeToken("LPAREN")
        self.consumeToken("RPAREN")
        self.consumeToken("LBRACE")
        body = []
        while self.currentToken() and self.currentToken().tokenType != "RBRACE":
            body.append(self.parseStatement())
        self.consumeToken("RBRACE")
        return self.astClasses["Function"](name, body)
    def parseStatement(self):
        token = self.currentToken()
        if token.tokenType in self.statementParseMap:
            return self.statementParseMap[token.tokenType]()
        elif token.tokenType in ("INT", "FLOAT", "CHAR") or (token.tokenType == "ID" and token.tokenValue == "string"):
            return self.parseDeclaration()
        else:
            expr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.astClasses["ExpressionStatement"](expr)
    def consumeDatatype(self):
        token = self.currentToken()
        if token.tokenType in ("INT", "FLOAT", "CHAR") or (token.tokenType == "ID" and (token.tokenValue in self.classNames or token.tokenValue == "string")):
            self.pos += 1
            return token
        raise SyntaxError("Expected datatype, got " + str(token))
    def parseReturn(self):
        self.consumeToken("RETURN")
        expr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.astClasses["Return"](expr)
    def parseExpression(self):
        return self.parseAssignment()
    def parseAssignment(self):
        node = self.parseComparison()
        if self.currentToken() and self.currentToken().tokenType == "EQ":
            self.consumeToken("EQ")
            right = self.parseAssignment()
            if node.__class__.__name__ in ("MemberAccess", "Var"):
                return self.astClasses["Assign"](node, right)
            raise SyntaxError("Invalid left-hand side for assignment")
        return node
    def parseBinary(self, lowerFn, ops, useTokenValue=True):
        node = lowerFn()
        while self.currentToken() and self.currentToken().tokenType in ops:
            opToken = self.consumeToken(self.currentToken().tokenType)
            op = opToken.tokenValue if useTokenValue else opToken.tokenType
            node = self.astClasses["BinOp"](op, node, lowerFn())
        return node
    def parseComparison(self):
        return self.parseBinary(self.parseAdditiveExpression, {"EQEQ", "NEQ", "LT", "GT", "LTE", "GTE"}, False)
    def parseAdditiveExpression(self):
        return self.parseBinary(self.parseMultiplicativeExpression, {"PLUS", "MINUS"})
    def parseMultiplicativeExpression(self):
        return self.parseBinary(self.parseFactor, {"MULT", "DIV", "MOD"})
    def parseFactor(self):
        token = self.currentToken()
        if token.tokenType in self.factorParseMap:
            return self.factorParseMap[token.tokenType]()
        raise SyntaxError("Unexpected token: " + str(token))
    def parseIdentifier(self):
        token = self.consumeToken("ID")
        name = token.tokenValue
        if self.currentToken() and self.currentToken().tokenType == "DOT":
            self.consumeToken("DOT")
            memberName = self.consumeToken("ID").tokenValue
            return self.astClasses["MemberAccess"](self.astClasses["Var"](name), memberName)
        elif self.currentToken() and self.currentToken().tokenType == "LPAREN":
            return self.parseFunctionCall(name)
        return self.astClasses["Var"](name)
    def parseParenthesizedExpression(self):
        self.consumeToken("LPAREN")
        node = self.parseExpression()
        self.consumeToken("RPAREN")
        return node
    def parseFunctionCall(self, name):
        self.consumeToken("LPAREN")
        args = []
        if self.currentToken() and self.currentToken().tokenType != "RPAREN":
            args.append(self.parseExpression())
            while self.currentToken() and self.currentToken().tokenType == "COMMA":
                self.consumeToken("COMMA")
                args.append(self.parseExpression())
        self.consumeToken("RPAREN")
        return self.astClasses["FunctionCall"](name, args)
    def parseIf(self):
        self.consumeToken("IF")
        if self.currentToken().tokenType == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        thenBranch = self.parseBlock()
        elseBranch = None
        if self.currentToken() and self.currentToken().tokenType == "ELSE":
            self.consumeToken("ELSE")
            elseBranch = [self.parseIf()] if self.currentToken() and self.currentToken().tokenType == "IF" else self.parseBlock()
        return self.astClasses["If"](condition, thenBranch, elseBranch)
    def parseWhile(self):
        self.consumeToken("WHILE")
        if self.currentToken().tokenType == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        body = self.parseBlock()
        return self.astClasses["While"](condition, body)
    def parseFor(self):
        self.consumeToken("FOR")
        self.consumeToken("LPAREN")
        init = self.parseStatement()
        condition = self.parseExpression()
        self.consumeToken("SEMICOLON")
        increment = self.parseExpression()
        self.consumeToken("RPAREN")
        body = self.parseBlock()
        return self.astClasses["For"](init, condition, increment, body)
    def parseDoWhile(self):
        self.consumeToken("DO")
        body = self.parseBlock()
        self.consumeToken("WHILE")
        if self.currentToken().tokenType == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.astClasses["DoWhile"](body, condition)
    def parseBlock(self):
        self.consumeToken("LBRACE")
        stmts = []
        while self.currentToken() and self.currentToken().tokenType != "RBRACE":
            stmts.append(self.parseStatement())
        self.consumeToken("RBRACE")
        return stmts

class CodeGen:
    def __init__(self, langDef):
        self.module = ir.Module(name="module")
        self.builder = None
        self.funcSymtab = {}
        self.stringCounter = 0
        self.programNode = None
        self.classStructTypes = {}
        self.declarePrintFunc()
        self.binOpMap = langDef["operators"]["binOpMap"]
        self.compMap = langDef["operators"]["compMap"]
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
    def __init__(self, langFile="lang.json"):
        self.langDef = json.load(open(langFile, "r"))
        self.astFactory = AstFactory(self.langDef)
        self.tokens = [(t["type"], t["regex"]) for t in self.langDef["tokens"]]
        self.lexer = Lexer(self.tokens)
    def compileSource(self, sourceCode, outputExe):
        tokens = self.lexer.lex(sourceCode)
        parser = Parser(tokens, self.astFactory.astClasses)
        ast = parser.parseProgram()
        codegen = CodeGen(self.langDef)
        codegen.programNode = ast
        llvmModule = codegen.generateCode(ast)
        self.compileModule(llvmModule, outputExe)
    def compileModule(self, llvmModule, outputExe):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        llvmIr = str(llvmModule)
        mod = llvm.parse_assembly(llvmIr)
        mod.verify()
        target = llvm.Target.from_default_triple()
        targetMachine = target.create_target_machine()
        objCode = targetMachine.emit_object(mod)
        objFilename = "output.o"
        with open(objFilename, "wb") as f:
            f.write(objCode)
        bcFilename = "output.bc"
        with open(bcFilename, "w") as f:
            f.write(str(llvmModule))
        linkedBcFilename = "linked.bc"
        subprocess.run(["llvm-link", bcFilename, "-o", linkedBcFilename], check=True)
        subprocess.run(["clang++", linkedBcFilename, "-o", outputExe, "-lstdc++", "-lm"], check=True)
        os.remove(objFilename)
        os.remove(bcFilename)
        os.remove(linkedBcFilename)
        print("Executable '" + outputExe + "' generated.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <sourceFile>")
        sys.exit(1)
    sourceFile = sys.argv[1]
    baseFilename = os.path.splitext(sourceFile)[0]
    outputExe = baseFilename + ".exe"
    with open(sourceFile, "r") as f:
        sourceCode = f.read()
    compiler = Compiler()
    compiler.compileSource(sourceCode, outputExe)
