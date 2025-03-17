from llvmlite import binding as llvm
from llvmlite import ir

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

    def declarePrintFunc(self):
        printType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        self.printFunc = ir.Function(self.module, printType, name="printf")

    def generateCode(self, node):
        if node.__class__.__name__ == "Program":
            self.programNode = node
            for cls in node.classes:
                self.codegenClassDeclaration(cls)
            for func in node.functions:
                self.Function(func)
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
        method = getattr(self, nodeType, None)
        if method is None:
            raise NotImplementedError("Codegen not implemented for " + nodeType)
        return method(node)

    def Return(self, node):
        return self.builder.ret(self.codegen(node.expr))

    def ExpressionStatement(self, node):
        return self.codegen(node.expr)

    def Num(self, node):
        return ir.Constant(ir.IntType(32), node.value)

    def FloatNum(self, node):
        return ir.Constant(ir.FloatType(), float(node.value))

    def String(self, node):
        return self.createStringConstant(node.value)

    def Char(self, node):
        return ir.Constant(ir.IntType(8), ord(node.value))

    def VarDecl(self, node):
        basicTypes = {
            "int": ir.IntType(32),
            "float": ir.FloatType(),
            "char": ir.IntType(8),
            "string": ir.PointerType(ir.IntType(8))
        }
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

    def BinOp(self, node):
        if node.op in self.binOpMap:
            intOp, floatOp, resName = self.binOpMap[node.op]
            return self.genArith(node, intOp, floatOp, resName)
        elif node.op in self.compMap:
            intCmp, floatCmp, resName = self.compMap[node.op]
            return self.genCompare(node, intCmp, floatCmp, resName)
        raise ValueError("Unknown binary operator " + node.op)

    def Var(self, node):
        info = self.funcSymtab.get(node.name)
        if info:
            return self.builder.load(info["addr"], name=node.name)
        raise NameError("Undefined variable: " + node.name)

    def FunctionCall(self, node):
        if node.name == "print":
            return self.PrintCall(node)
        raise NameError("Unknown function: " + node.name)

    def PrintCall(self, node):
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

    def MemberAccess(self, node):
        objInfo = self.funcSymtab[node.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], node.memberName)
        ptr = self.builder.gep(self.builder.load(objInfo["addr"]), 
                               [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], 
                               name="memberPtr")
        return self.builder.load(ptr, name=node.memberName)

    def Assign(self, node):
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

    def MemberAssignment(self, memberNode, val):
        objInfo = self.funcSymtab[memberNode.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], memberNode.memberName)
        ptr = self.builder.gep(self.builder.load(objInfo["addr"]), 
                               [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], 
                               name="memberPtr")
        self.builder.store(val, ptr)
        return val

    def If(self, node):
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

    def While(self, node):
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

    def For(self, node):
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

    def DoWhile(self, node):
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

    def ClassDeclaration(self, node):
        members = [ir.IntType(32) for _ in node.members]
        self.classStructTypes[node.name] = ir.LiteralStructType(members)

    def Function(self, node):
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
