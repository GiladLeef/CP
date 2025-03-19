import subprocess
import os
import sys
from lexer import Lexer
from parser import Parser
from codegen import Codegen
from llvmlite import binding as llvm
from lang import language

def processImports(filePath, processedFiles=None):
    if processedFiles is None:
        processedFiles = set()

    if filePath in processedFiles:
        return ""

    processedFiles.add(filePath)

    with open(filePath, 'r') as f:
        content = f.readlines()

    resultContent = []
    importsToProcess = []

    for line in content:
        if line.startswith("import") and ".cp" in line:
            importFile = line.split("import")[1].strip().replace(".cp", "") + ".cp"
            importsToProcess.append(importFile)
            resultContent.append("// " + line) 
        else:
            resultContent.append(line)

    for importFile in importsToProcess:
        importFilePath = os.path.join(os.path.dirname(filePath), importFile)
        importedContent = processImports(importFilePath, processedFiles)
        resultContent.insert(0, importedContent) 

    return "".join(resultContent)

class Compiler:
    def __init__(self):
        self.tokens = [(t["type"], t["regex"]) for t in language["tokens"]]
        self.lexer = Lexer(self.tokens)

    def compileSource(self, sourceCode, outputExe):
        tokens = self.lexer.lex(sourceCode)
        parser = Parser(language, tokens)
        ast = parser.parseProgram()
        codegen = Codegen(language)
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
        print(f"Executable '{outputExe}' generated.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <sourceFile>")
        sys.exit(1)

    sourceFile = sys.argv[1]

    finalContent = processImports(sourceFile)

    baseFilename = os.path.splitext(sourceFile)[0]
    outputExe = baseFilename + ".exe"

    compiler = Compiler()
    compiler.compileSource(finalContent, outputExe)
