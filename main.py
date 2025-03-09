# main.py
import sys
import os
from lexer import lex
from parser import Parser
from codegen import CodeGen
from llvmlite import binding as llvm
import subprocess

def compile_module(llvm_module, output_exe):
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
    with open(bc_filename, 'w') as f:
        f.write(str(llvm_module))
    linked_bc_filename = "linked.bc"
    subprocess.run(['llvm-link', bc_filename, '-o', linked_bc_filename], check=True)
    subprocess.run(['clang++', linked_bc_filename, '-o', output_exe, '-lstdc++', '-lm'], check=True)
    os.remove(obj_filename)
    os.remove(bc_filename)
    os.remove(linked_bc_filename)
    print(f"Executable '{output_exe}' generated.")


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
