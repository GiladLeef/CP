# This file is part of the C+ project.
#
# Copyright (C) 2025 GiladLeef
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from llvmlite import ir
from typing import Literal

OS_LITERAL = Literal['linux', 'windows']

class Codegen:
    def __init__(self, language):
        self.language = language
        self.module = ir.Module(name="module")
        self.builtin_funcs = (
            "print",
            "write",
            "exit",
            "fork",
            "execve",
            "malloc",
            "free"
        )
        self.builtin_funcs_call = {
            "print": self.PrintCall,
            "write": self.WriteCall,
            "exit": self.ExitCall,
            "fork": self.ForkCall,
            "execve": self.ExecveCall,
            "malloc": self.MallocCall,
            "free": self.FreeCall
        }
        self.builder = None
        self.funcSymtab = {}
        self.stringCounter = 0
        self.programNode = None
        self.classStructTypes = {}
        self.declareStdFuncs()
        self.binOpMap = language["operators"]["binOpMap"]
        self.compMap = language["operators"]["compMap"]
        self.datatypes = language["datatypes"]
        self.arrayTypesCache = {}
    def declareStdFuncs(self, os:OS_LITERAL="linux"):
        if os == "linux":
            printType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
            self.printFunc = ir.Function(self.module, printType, name="printf")

            writeType = ir.FunctionType(ir.IntType(32), [ir.IntType(32), ir.PointerType(ir.IntType(8)), ir.IntType(32)], var_arg=False)
            self.writeFunc = ir.Function(self.module, writeType, name="write")

            readType = ir.FunctionType(ir.IntType(32), [ir.IntType(32), ir.PointerType(ir.IntType(8)), ir.IntType(32)], var_arg=False)
            self.readFunc = ir.Function(self.module, readType, name="read")

            exitType = ir.FunctionType(ir.VoidType(), [ir.IntType(32)], var_arg=False)
            self.exitFunc = ir.Function(self.module, exitType, name="exit")

            forkType = ir.FunctionType(ir.IntType(32), [], var_arg=False)
            self.forkFunc = ir.Function(self.module, forkType, name="fork")

            execveType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.PointerType(ir.IntType(8))), ir.PointerType(ir.PointerType(ir.IntType(8)))], var_arg=False)
            self.execveFunc = ir.Function(self.module, execveType, name="execve")

            mallocType = ir.FunctionType(ir.PointerType(ir.IntType(8)), [ir.IntType(32)], var_arg=False)
            self.mallocFunc = ir.Function(self.module, mallocType, name="malloc")

            freeType = ir.FunctionType(ir.VoidType(), [ir.PointerType(ir.IntType(8))], var_arg=False)
            self.freeFunc = ir.Function(self.module, freeType, name="free")

            memcpyType = ir.FunctionType(ir.PointerType(ir.IntType(8)), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8)), ir.IntType(32)], var_arg=False)
            self.memcpyFunc = ir.Function(self.module, memcpyType, name="memcpy")

            strlenType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=False)
            self.strlenFunc = ir.Function(self.module, strlenType, name="strlen")

            strcmpType = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))], var_arg=False)
            self.strcmpFunc = ir.Function(self.module, strcmpType, name="strcmp")

            memsetType = ir.FunctionType(ir.PointerType(ir.IntType(8)), [ir.PointerType(ir.IntType(8)), ir.IntType(32), ir.IntType(32)], var_arg=False)
            self.memsetFunc = ir.Function(self.module, memsetType, name="memset")






    def generateCode(self, node):
        if node.__class__.__name__ == "Program":
            self.programNode = node
            for cls in node.classes:
                self.ClassDeclaration(cls)
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
                for i, field in enumerate(cls.fields):
                    if field.name == memberName:
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
        if floatOp is not None and (left.type == ir.FloatType() or right.type == ir.FloatType()):
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
        if node.datatypeName.endswith("[]"):
            baseTypeName = node.datatypeName[:-2]
            if baseTypeName in self.datatypes:
                elemType = self.datatypes[baseTypeName]
            elif baseTypeName in self.classStructTypes:
                elemType = self.classStructTypes[baseTypeName]
            else:
                raise ValueError("Unknown datatype: " + baseTypeName)

            if node.init and node.init.__class__.__name__ == "ArrayLiteral":
                arrayLiteral = self.codegen(node.init)
                numElements = len(node.init.elements)
                arrayType = ir.ArrayType(elemType, numElements)
                addr = self.builder.alloca(arrayType, name=node.name)

                self.funcSymtab[node.name] = {
                    "addr": addr, 
                    "datatypeName": baseTypeName, 
                    "isArray": True,
                    "size": numElements
                }

                for i in range(numElements):
                    srcPtr = self.builder.gep(arrayLiteral, [
                        ir.Constant(ir.IntType(32), 0),
                        ir.Constant(ir.IntType(32), i)
                    ], name=f"src_ptr_{i}")

                    dstPtr = self.builder.gep(addr, [
                        ir.Constant(ir.IntType(32), 0),
                        ir.Constant(ir.IntType(32), i)
                    ], name=f"dst_ptr_{i}")

                    val = self.builder.load(srcPtr, name=f"elem_{i}")
                    self.builder.store(val, dstPtr)

                return addr
            else:
                size = 10
                arrayType = ir.ArrayType(elemType, size)
                addr = self.builder.alloca(arrayType, name=node.name)

                self.funcSymtab[node.name] = {
                    "addr": addr, 
                    "datatypeName": baseTypeName, 
                    "isArray": True,
                    "size": size
                }
                return addr

        if node.datatypeName in self.datatypes:
            varType = self.datatypes[node.datatypeName]
            addr = self.builder.alloca(varType, name=node.name)
        elif node.datatypeName in self.classStructTypes:
            structType = self.classStructTypes[node.datatypeName]
            addr = self.builder.alloca(structType, name=node.name)
        else:
            raise ValueError("Unknown datatype: " + node.datatypeName)

        if node.init:
            init_val = self.codegen(node.init)
            if node.datatypeName == "float" and init_val.type == ir.IntType(32):
                init_val = self.builder.sitofp(init_val, ir.FloatType())
            self.builder.store(init_val, addr)

        self.funcSymtab[node.name] = {"addr": addr, "datatypeName": node.datatypeName}
        return addr

    def ArrayDecl(self, node):
        elemTypeName = node.elemType
        if elemTypeName in self.datatypes:
            elemType = self.datatypes[elemTypeName]
        elif elemTypeName in self.classStructTypes:
            elemType = self.classStructTypes[elemTypeName]
        else:
            raise ValueError("Unknown element type: " + elemTypeName)

        sizeVal = None
        if node.size:
            sizeVal = self.codegen(node.size)
            if not isinstance(sizeVal, ir.Constant):

                mallocFunc = self.getMallocFunc()
                byteSize = self.builder.mul(sizeVal, ir.Constant(ir.IntType(32), 4), name="bytesize")
                arrayPtr = self.builder.call(mallocFunc, [byteSize], name="arrayptr")
                arrayPtr = self.builder.bitcast(arrayPtr, ir.PointerType(elemType), name="typedptr")
                addr = self.builder.alloca(ir.PointerType(elemType), name=node.name)
                self.builder.store(arrayPtr, addr)
                self.funcSymtab[node.name] = {
                    "addr": addr, 
                    "datatypeName": elemTypeName, 
                    "isArray": True,
                    "sizeVar": sizeVal
                }
                return addr
            else:
                size = int(sizeVal.constant)  
        else:
            size = 10  

        arrayType = ir.ArrayType(elemType, size)
        addr = self.builder.alloca(arrayType, name=node.name)

        self.funcSymtab[node.name] = {
            "addr": addr, 
            "datatypeName": elemTypeName, 
            "isArray": True,
            "size": size
        }
        return addr

    def ArrayLiteral(self, node):
        if not node.elements:
            return ir.Constant(ir.ArrayType(ir.IntType(32), 0), [])

        firstElem = self.codegen(node.elements[0])
        elemType = firstElem.type

        arrayType = ir.ArrayType(elemType, len(node.elements))
        array = self.builder.alloca(arrayType, name="array_literal")

        for i, elem in enumerate(node.elements):
            elemValue = self.codegen(elem)
            if elemValue.type != elemType:
                if elemType == ir.FloatType() and elemValue.type == ir.IntType(32):
                    elemValue = self.builder.sitofp(elemValue, ir.FloatType())

            elemPtr = self.builder.gep(array, [
                ir.Constant(ir.IntType(32), 0),
                ir.Constant(ir.IntType(32), i)
            ], name=f"elem_ptr_{i}")
            self.builder.store(elemValue, elemPtr)

        return array

    def ArrayAccess(self, node):
        arrayInfo = self.funcSymtab.get(node.array.name)
        if not arrayInfo:
            raise NameError(f"Undefined array: {node.array.name}")

        idx = self.codegen(node.index)
        arrayAddr = arrayInfo["addr"]

        if isinstance(idx, ir.Constant):

            if "size" in arrayInfo and idx.constant >= arrayInfo["size"]:
                raise IndexError(f"Array index {idx.constant} out of bounds for array of size {arrayInfo['size']}")
        else:

            if "size" in arrayInfo:
                size = ir.Constant(ir.IntType(32), arrayInfo["size"])
                is_valid = self.builder.icmp_signed("<", idx, size, name="bounds_check")
                with self.builder.if_then(is_valid, likely=True):
                    pass

        if "isArray" in arrayInfo and "sizeVar" in arrayInfo:

            arrayPtr = self.builder.load(arrayAddr, name="array_ptr")
            elemPtr = self.builder.gep(arrayPtr, [idx], name="elem_ptr")
        else:

            elemPtr = self.builder.gep(arrayAddr, [
                ir.Constant(ir.IntType(32), 0),
                idx
            ], name="elem_ptr")

        return self.builder.load(elemPtr, name="elem_value")

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

        if info is None:
            raise NameError("Undefined variable: " + node.name)

        ptr = info["addr"] if isinstance(info, dict) else info

        return self.builder.load(ptr, name=node.name)

    def FunctionCall(self, node):
        if node.callee.__class__.__name__ == "Var":
            if node.callee.name in self.builtin_funcs:
                return self.builtin_funcs_call[node.callee.name](node)
            func = self.module.get_global(node.callee.name)
            if not func:
                raise NameError("Unknown function: " + node.callee.name)
            llvmArgs = []
            for arg in node.args:
                llvmArgs.append(self.codegen(arg))
            return self.builder.call(func, llvmArgs)
        elif node.callee.__class__.__name__ == "MemberAccess":
            obj = self.funcSymtab[node.callee.objectExpr.name]["addr"]
            methodName = node.callee.memberName
            info = self.funcSymtab.get(node.callee.objectExpr.name)
            if not info:
                raise NameError("Undefined variable: " + node.callee.objectExpr.name)
            className = info["datatypeName"]
            qualifiedName = f"{className}_{methodName}"
            llvmArgs = [obj]
            for arg in node.args:
                llvmArgs.append(self.codegen(arg))
            func = self.module.get_global(qualifiedName)
            if not func:
                raise NameError("Method " + qualifiedName + " not defined.")
            return self.builder.call(func, llvmArgs)
        else:
            raise SyntaxError("Invalid function call callee.")

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
    def WriteCall(self, node):
        llvmArgs = []
        fmtParts = []
        
        val = self.codegen(node.args[0])
        llvmArgs.append(val)
        
        val = self.codegen(node.args[1])
        llvmArgs.append(val)

        val = self.codegen(node.args[2])
        llvmArgs.append(val)
        
        return self.builder.call(self.writeFunc, llvmArgs)


    def ExitCall(self, node):
        val = self.codegen(node.args[0])
        return self.builder.call(self.exitFunc, [val])


    def ForkCall(self, node):
        return self.builder.call(self.forkFunc, [])


    def ExecveCall(self, node):
        fmtParts = []
        llvmArgs = []
        
        val = self.codegen(node.args[0])
        llvmArgs.append(val)
        
        val = self.codegen(node.args[1])
        llvmArgs.append(val)

        val = self.codegen(node.args[2])
        llvmArgs.append(val)

        return self.builder.call(self.execveFunc, llvmArgs)


    def MallocCall(self, node):
        val = self.codegen(node.args[0])
        return self.builder.call(self.mallocFunc, [val])


    def FreeCall(self, node):
        val = self.codegen(node.args[0])
        return self.builder.call(self.freeFunc, [val])
    









    def MemberAccess(self, node):
        objInfo = self.funcSymtab[node.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], node.memberName)
        ptr = self.builder.gep(objInfo["addr"], [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name="memberPtr")
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
            return self.MemberAssignment(node.left, self.codegen(node.right))
        elif node.left.__class__.__name__ == "ArrayAccess":
            return self.ArrayElementAssignment(node.left, self.codegen(node.right))
        raise SyntaxError("Invalid left-hand side for assignment")

    def MemberAssignment(self, memberNode, val):
        objInfo = self.funcSymtab[memberNode.objectExpr.name]
        idx = self.getMemberIndex(objInfo["datatypeName"], memberNode.memberName)
        ptr = self.builder.gep(objInfo["addr"], [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)], name="memberPtr")

        self.builder.store(val, ptr)
        return val

    def ArrayElementAssignment(self, arrayAccessNode, val):
        arrayInfo = self.funcSymtab.get(arrayAccessNode.array.name)
        if not arrayInfo:
            raise NameError(f"Undefined array: {arrayAccessNode.array.name}")

        idx = self.codegen(arrayAccessNode.index)
        arrayAddr = arrayInfo["addr"]

        if "isArray" in arrayInfo and "sizeVar" in arrayInfo:

            arrayPtr = self.builder.load(arrayAddr, name="array_ptr")
            elemPtr = self.builder.gep(arrayPtr, [idx], name="elem_ptr")
        else:

            elemPtr = self.builder.gep(arrayAddr, [
                ir.Constant(ir.IntType(32), 0),
                idx
            ], name="elem_ptr")

        self.builder.store(val, elemPtr)
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
        structType = ir.global_context.get_identified_type(node.name)
        fieldTypes = []
        for field in node.fields:
            if field.datatypeName in self.datatypes:
                fieldTypes.append(self.datatypes[field.datatypeName])
            elif field.datatypeName in self.classStructTypes:
                fieldTypes.append(self.classStructTypes[field.datatypeName])
            else:
                raise ValueError("Unknown datatype: " + field.datatypeName)

        structType.set_body(*fieldTypes)
        self.classStructTypes[node.name] = structType
        for method in node.methods:
            self.MethodDecl(method)

    def MethodDecl(self, node):
        if node.className not in self.classStructTypes:
            raise ValueError("Unknown class in method: " + node.className)
        classType = self.classStructTypes[node.className]
        paramTypes = [ir.PointerType(classType)]

        for param in node.parameters:
            dt = param.datatypeName
            if dt in self.datatypes:
                paramTypes.append(self.datatypes[dt])
            elif dt in self.classStructTypes:
                paramTypes.append(ir.PointerType(self.classStructTypes[dt]))
            else:
                raise ValueError("Unknown datatype in method parameter: " + dt)
        returnType = self.datatypes[node.returnType] if hasattr(node, "returnType") and node.returnType in self.datatypes else ir.IntType(32)

        funcType = ir.FunctionType(returnType, paramTypes)
        funcName = f"{node.className}_{node.name}"
        if funcName in self.module.globals:
            return self.module.globals[funcName]
        func = ir.Function(self.module, funcType, name=funcName)
        entry = func.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.funcSymtab = {}
        self.funcSymtab["self"] = {"addr": func.args[0], "datatypeName": node.className}
        for i, param in enumerate(node.parameters, start=1):
            self.funcSymtab[param.name] = {"addr": func.args[i], "datatypeName": param.datatypeName}
        retval = None
        for stmt in node.body:
            retval = self.codegen(stmt)
        if not self.builder.block.terminator:
            self.builder.ret(retval if retval else ir.Constant(ir.IntType(32), 0))
    def Function(self, node):
        declaration = False
        if node.body == None:
            declaration = True
        retTypeStr = node.returnType if hasattr(node, "returnType") else "int"
        if retTypeStr in self.datatypes:
            returnType = self.datatypes[retTypeStr]
        else:
            returnType = ir.IntType(32)
        if len(node.args) == 0:  
            funcType = ir.FunctionType(returnType, [], var_arg=False)
        else:
            funcType = ir.FunctionType(returnType, [self.datatypes[arg_type] for arg_type, _ in node.args], var_arg=True)
        func = ir.Function(self.module, funcType, name=node.name)
        if not declaration:
            entry = func.append_basic_block("entry")
            self.builder = ir.IRBuilder(entry)
            self.funcSymtab = {}
            if len(node.args) != 0:
                for i, (_, name) in enumerate(node.args):
                    func.args[i].name = name
                    ptr = self.builder.alloca(func.args[i].type, name=name + "_ptr")
                    self.builder.store(func.args[i], ptr)
                    self.funcSymtab[name] = ptr
            
        
            for stmt in node.body:
                retval = self.codegen(stmt)

            if not self.builder.block.terminator:
                self.builder.ret(retval if retval is not None else ir.Constant(returnType, 0))

    def NewExpr(self, node):
        if node.className not in self.classStructTypes:
            raise ValueError("Unknown class: " + node.className)
        structType = self.classStructTypes[node.className]
        obj = self.builder.alloca(structType, name="objtmp")
        return obj

    def getMallocFunc(self):
        if hasattr(self, "mallocFunc"):
            return self.mallocFunc

        mallocType = ir.FunctionType(
            ir.PointerType(ir.IntType(8)),
            [ir.IntType(32)]
        )
        self.mallocFunc = ir.Function(self.module, mallocType, name="malloc")
        return self.mallocFunc