# parser.py
from ast import *
from lexer import lex

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.class_names = set()
        self.statement_parse_map = {
            'RETURN': self.parse_return,
            'IF': self.parse_if,
            'WHILE': self.parse_while,
            'FOR': self.parse_for,
            'DO': self.parse_do_while,
        }
    def current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    def consume(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        raise SyntaxError(f"Expected token {token_type}, got {token}")
    def parse(self):
        functions = []
        classes = []
        while self.current() is not None:
            if self.current().type == 'CLASS':
                class_decl = self.parse_class_declaration()
                classes.append(class_decl)
                self.class_names.add(class_decl.name)
            elif self.current().type in ('INT', 'FLOAT', 'CHAR', 'ID') and (self.current().type != 'ID' or self.current().value != 'class'):
                functions.append(self.parse_function())
            else:
                self.consume(self.current().type)
        return Program(functions, classes)
    def parse_class_declaration(self):
        self.consume('CLASS')
        class_name = self.consume('ID').value
        self.consume('LBRACE')
        members = []
        while self.current() and self.current().type != 'RBRACE':
            member = self.parse_declaration_member()
            if not isinstance(member, VarDecl):
                raise SyntaxError("Class members must be variable declarations")
            members.append(member)
        self.consume('RBRACE')
        return ClassDecl(class_name, members)
    def parse_declaration_member(self):
        data_type_token = self.consume_datatype()
        var_name = self.consume('ID').value
        self.consume('SEMICOLON')
        return VarDecl(var_name, None, datatype_name=data_type_token.value)
    def parse_declaration(self):
        data_type_token = self.consume_datatype()
        var_name = self.consume('ID').value
        datatype_name = data_type_token.value
        if self.current() and self.current().type == 'EQ':
            self.consume('EQ')
            init_expr = self.parse_expression()
            self.consume('SEMICOLON')
            return VarDecl(var_name, init_expr, datatype_name=datatype_name)
        self.consume('SEMICOLON')
        return VarDecl(var_name, None, datatype_name=datatype_name)
    def parse_function(self):
        data_type_token = self.consume_datatype()
        name = self.consume('ID').value
        self.consume('LPAREN')
        self.consume('RPAREN')
        self.consume('LBRACE')
        body = []
        while self.current() and self.current().type != 'RBRACE':
            body.append(self.parse_statement())
        self.consume('RBRACE')
        return Function(name, body)
    def parse_statement(self):
        token = self.current()
        if token.type in self.statement_parse_map:
            return self.statement_parse_map[token.type]()
        elif token.type in ('INT', 'FLOAT', 'CHAR') or (token.type == 'ID' and token.value == 'string'):
            return self.parse_declaration()
        else:
            expr = self.parse_expression()
            self.consume('SEMICOLON')
            return ExpressionStatement(expr)
    def consume_datatype(self):
        token = self.current()
        if token.type in ('INT', 'FLOAT', 'CHAR') or (token.type == 'ID' and (token.value in self.class_names or token.value == 'string')):
            self.pos += 1
            return token
        raise SyntaxError(f"Expected datatype, got {token}")
    def parse_return(self):
        self.consume('RETURN')
        expr = self.parse_expression()
        self.consume('SEMICOLON')
        return Return(expr)
    def parse_expression(self):
        node = self.parse_assignment()
        return node
    def parse_assignment(self):
        node = self.parse_comparison()
        if self.current() and self.current().type == 'EQ':
            self.consume('EQ')
            right = self.parse_assignment()
            if isinstance(node, MemberAccess) or isinstance(node, Var):
                return Assign(node, right)
            raise SyntaxError("Invalid left-hand side for assignment")
        return node
    def parse_comparison(self):
        node = self.parse_additive_expression()
        while self.current() and self.current().type in ('EQEQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
            op_token = self.consume(self.current().type)
            op = op_token.type
            right = self.parse_additive_expression()
            node = BinOp(op, node, right)
        return node
    def parse_additive_expression(self):
        node = self.parse_multiplicative_expression()
        while self.current() and self.current().type in ('PLUS', 'MINUS'):
            op = self.consume(self.current().type).value
            right = self.parse_multiplicative_expression()
            node = BinOp(op, node, right)
        return node
    def parse_multiplicative_expression(self):
        node = self.parse_factor()
        while self.current() and self.current().type in ('MULT', 'DIV', 'MOD'):
            op = self.consume(self.current().type).value
            right = self.parse_factor()
            node = BinOp(op, node, right)
        return node
    def parse_factor(self):
        token = self.current()
        if token.type == 'NUMBER':
            self.consume('NUMBER')
            return Num(token.value)
        elif token.type == 'FLOAT_NUMBER':
            self.consume('FLOAT_NUMBER')
            return FloatNum(token.value)
        elif token.type == 'STRING':
            self.consume('STRING')
            return String(token.value)
        elif token.type == 'CHAR_LITERAL':
            self.consume('CHAR_LITERAL')
            return Char(token.value)
        elif token.type == 'ID':
            self.consume('ID')
            name = token.value
            if self.current() and self.current().type == 'DOT':
                self.consume('DOT')
                member_name = self.consume('ID').value
                return MemberAccess(Var(name), member_name)
            elif self.current() and self.current().type == 'LPAREN':
                return self.parse_function_call(name)
            return Var(name)
        elif token.type == 'LPAREN':
            self.consume('LPAREN')
            node = self.parse_expression()
            self.consume('RPAREN')
            return node
        raise SyntaxError(f"Unexpected token: {token}")
    def parse_function_call(self, func_name):
        self.consume('LPAREN')
        args = []
        if self.current() and self.current().type != 'RPAREN':
            args.append(self.parse_expression())
            while self.current() and self.current().type == 'COMMA':
                self.consume('COMMA')
                args.append(self.parse_expression())
        self.consume('RPAREN')
        return FunctionCall(func_name, args)
    def parse_if(self):
        self.consume('IF')
        if self.current().type == 'LPAREN':
            self.consume('LPAREN')
            condition = self.parse_expression()
            self.consume('RPAREN')
        else:
            condition = self.parse_expression()
        then_branch = self.parse_block()
        else_branch = None
        if self.current() and self.current().type == 'ELSE':
            self.consume('ELSE')
            if self.current() and self.current().type == 'IF':
                else_branch = [self.parse_if()]
            else:
                else_branch = self.parse_block()
        return If(condition, then_branch, else_branch)
    def parse_while(self):
        self.consume('WHILE')
        if self.current().type == 'LPAREN':
            self.consume('LPAREN')
            condition = self.parse_expression()
            self.consume('RPAREN')
        else:
            condition = self.parse_expression()
        body = self.parse_block()
        return While(condition, body)
    def parse_for(self):
        self.consume('FOR')
        self.consume('LPAREN')
        init = self.parse_statement()
        condition = self.parse_expression()
        self.consume('SEMICOLON')
        increment = self.parse_expression()
        self.consume('RPAREN')
        body = self.parse_block()
        return For(init, condition, increment, body)
    def parse_do_while(self):
        self.consume('DO')
        body = self.parse_block()
        self.consume('WHILE')
        if self.current().type == 'LPAREN':
            self.consume('LPAREN')
            condition = self.parse_expression()
            self.consume('RPAREN')
        else:
            condition = self.parse_expression()
        self.consume('SEMICOLON')
        return DoWhile(body, condition)
    def parse_block(self):
        self.consume('LBRACE')
        stmts = []
        while self.current() and self.current().type != 'RBRACE':
            stmts.append(self.parse_statement())
        self.consume('RBRACE')
        return stmts
