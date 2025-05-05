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

import subprocess
import os
import sys
from lexer import Lexer
from parser import Parser
from codegen import Codegen
try:    
    from llvmlite import binding as llvm
except:
    print("please install llvm lite")
    exit(1)
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

    def compileSource(self, sourceCode, outputExe, flags, cflag=False, Sflag=False):
        tokens = self.lexer.lex(sourceCode)
        parser = Parser(language, tokens)
        ast = parser.parseProgram()
        codegen = Codegen(language)
        codegen.programNode = ast
        llvmModule = codegen.generateCode(ast)
        self.compileModule(llvmModule, outputExe, flags, cflag, Sflag)

    def compileModule(self, llvmModule, outputExe, flags, cflag=False, Sflag=False):
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
        try:
            subprocess.run(["llvm-link", bcFilename, "-o", linkedBcFilename], check=True)
            if not cflag and not Sflag:
                subprocess.run(["clang++", *flags, linkedBcFilename, "-o", outputExe, "-lstdc++", "-lm"], check=True)
                
                print(f"Executable '{outputExe}' generated.")
            else:
                if not Sflag and cflag:
                    subprocess.run(["clang++", *flags, linkedBcFilename, "-c", "-o", outputExe], check=True)
                    print(f"Object '{outputExe} generated, you can now link it")
                else:
                    subprocess.run(["clang++", *flags, linkedBcFilename, "-S", "-o", outputExe], check=True)
                    print(f"Asm file '{outputExe}' generated")
        finally:
            os.remove(objFilename)
            os.remove(bcFilename)
            os.remove(linkedBcFilename)
def printUsage():
    print("Usage: python compiler.py [OPTIONS] <sourceFile>")
    print("OPTIONS:")
    print("\t-o [OUTFILE]   Sets the output file")
    print("\t-h             Help page")
    print("\t-c             Create a .o file")
    print("\t-g             Add debug symbols")
    print("\t-O[0-3]        Optimise Level")
    sys.exit(1)
import sys
import os

if __name__ == "__main__":
    valid_optimizations = ['-O3', '-O2', '-O1', '-O0']
    flags = []
    cflag = False
    Sflag = False
    outputExe = None
    sourceFile = None

    args = sys.argv[1:]

    if not args or '-h' in args:
        printUsage()

    if '-c' in args:
        args.remove('-c')
        cflag = True
    elif '-S' in args:
        args.remove('-S')
        Sflag = True
    if '-g' in args:
        args.remove('-g')
        flags.append('-g')
    
    for opt in valid_optimizations:
        if opt in args:
            args.remove(opt)
            flags.append(opt)
            break

    if '-o' in args:
        try:
            o_index = args.index('-o')
            outputExe = args[o_index + 1]
            del args[o_index:o_index + 2]
        except (IndexError, ValueError):
            printUsage()

    if not args:
        printUsage()
    sourceFile = args[0]

    finalContent = processImports(sourceFile)
    baseFilename = os.path.splitext(sourceFile)[0]
    outputExe = outputExe or baseFilename + ".exe"

    compiler = Compiler()
    compiler.compileSource(finalContent, outputExe, flags, cflag, Sflag)
