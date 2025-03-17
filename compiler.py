import json
import subprocess
import os
import sys
from lexer import Lexer
from parser import Parser
from codegen import CodeGen
from llvmlite import binding as llvm

class Compiler:
    def __init__(self, langFile="lang.json"):
        self.langDef = json.load(open(langFile, "r"))
        self.tokens = [(t["type"], t["regex"]) for t in self.langDef["tokens"]]
        self.lexer = Lexer(self.tokens)

    def compileSource(self, sourceCode, outputExe):
        tokens = self.lexer.lex(sourceCode)
        parser = Parser(tokens, self.langDef)
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

