# compiler.py
import sys
import os
from lexer import lex
from parser import Parser
from codegen import CodeGen
from codegen import compile_module

def compile_generated_module(llvm_module, output_exe):
    compile_module(llvm_module, output_exe)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <source_file>")
        sys.exit(1)
    source_file = sys.argv[1]
    base_filename = os.path.splitext(source_file)[0]
    output_exe = base_filename + ".exe"
    
    with open(source_file, "r") as f:
        source_code = f.read()
    
    tokens = lex(source_code)    
    parser = Parser(tokens)
    ast = parser.parse()
    codegen = CodeGen()
    codegen.program_node = ast
    llvm_module = codegen.generate_code(ast)
    compile_generated_module(llvm_module, output_exe)
