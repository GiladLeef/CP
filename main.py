import sys
import os
from compiler import Compiler

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
