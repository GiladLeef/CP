from lexer import AstFactory
import lexer
from llvmlite import ir
class Parser:
    def __init__(self, language, tokens):
        self.language = language
        self.tokens = tokens
        self.pos = 0
        self.astClasses = AstFactory(language).astClasses
        self.classNames = set()
        self.statementParseMap = {}
        for key, funcName in language["statementParseMap"].items():
            self.statementParseMap[key] = getattr(self, funcName)
        self.factorParseMap = {}
        for key, value in language["factorParseMap"].items():
            if isinstance(value, dict):
                method = getattr(self, value["method"])
                args = value["args"]
                self.factorParseMap[key] = (lambda m=method, a=args: m(*a))
            else:
                self.factorParseMap[key] = getattr(self, value)
        self.op_precedences = language["operators"]["precedences"]
        self.datatypes = ("INT", "FLOAT", "CHAR")

    def currentToken(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def match(self, tokenType):
        token = self.currentToken()
        return token and token.tokenType == tokenType
        
    def peek(self, offset=1) -> lexer.Token:
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else None

    def advance(self):
        token = self.currentToken()
        self.pos += 1
        return token
        
    def consumeToken(self, tokenType) -> lexer.Token:
        if self.match(tokenType):
            return self.advance()
        raise SyntaxError(f"Expected token {tokenType}, got {self.currentToken()}")

    def consumePairedTokens(self, openToken, closeToken, parseFunc):
        self.consumeToken(openToken)
        result = parseFunc()
        self.consumeToken(closeToken)
        return result
        
    def parseLiteral(self, tokenType, astName):
        token = self.consumeToken(tokenType)
        return self.astClasses[astName](token.tokenValue)

    def parseProgram(self):
        functions = []
        classes = []
        while self.currentToken() is not None:
            if self.match("CLASS"):
                classDecl = self.parseClassDeclaration()
                classes.append(classDecl)
                self.classNames.add(classDecl.name)
            elif self.isDatatype(self.currentToken()):
                functions.append(self.parseFunction())
            else:
                self.advance()
        return self.astClasses["Program"](functions, classes)

    def parseClassDeclaration(self):
        self.consumeToken("CLASS")
        className = self.consumeToken("ID").tokenValue
        fields, methods = self.parseBodyMembers("LBRACE", "RBRACE", 
                                                lambda: self.parseClassMember(className))
        return self.astClasses["ClassDecl"](className, fields, methods)
        
    def parseBodyMembers(self, openToken, closeToken, parseMemberFunc):
        self.consumeToken(openToken)
        fields = []
        methods = []
        while self.currentToken() and not self.match(closeToken):
            member = parseMemberFunc()
            if member.__class__.__name__ == "MethodDecl":
                methods.append(member)
            else:
                fields.append(member)
        self.consumeToken(closeToken)
        return fields, methods

    def parseClassMember(self, className):
        dataTypeToken = self.consumeDatatype()
        nameToken = self.consumeToken("ID")
        if self.match("LPAREN"):
            return self.parseMethodDeclaration(dataTypeToken, nameToken, className)
        else:
            self.consumeToken("SEMICOLON")
            return self.createVarDecl(nameToken.tokenValue, None, dataTypeToken.tokenValue)

    def parseMethodDeclaration(self, returnTypeToken, nameToken, className):
        methodName = nameToken.tokenValue
        params = self.consumePairedTokens("LPAREN", "RPAREN", 
                                         lambda: self.parseDelimitedList("RPAREN", "COMMA", self.parseParameter))
        body = self.parseBlock()
        return self.astClasses["MethodDecl"](methodName, params, body, className, returnTypeToken.tokenValue)

    def parseParameter(self):
        dataTypeToken = self.consumeDatatype()
        idToken = self.consumeToken("ID")
        return self.createVarDecl(idToken.tokenValue, None, dataTypeToken.tokenValue)
        
    def createVarDecl(self, name, init, typeName):
        return self.astClasses["VarDecl"](name, init, typeName)

    def parseDelimitedList(self, endToken, delimiterToken, parseFunc):
        result = []
        if not self.match(endToken):
            result.append(parseFunc())
            while self.match(delimiterToken):
                self.consumeToken(delimiterToken)
                result.append(parseFunc())
        return result

    def parseDeclaration(self):
        dataTypeToken = self.consumeDatatype()
        dataTypeName = dataTypeToken.tokenValue

        if self.match("LBRACKET"):
            self.consumeToken("LBRACKET")
            size = None if self.match("RBRACKET") else self.parseExpression()
            self.consumeToken("RBRACKET")
            varName = self.consumeToken("ID").tokenValue
            
            if self.match("EQ"):
                return self.parseInitializedDeclaration(varName, f"{dataTypeName}[]")
            
            self.consumeToken("SEMICOLON")
            return self.astClasses["ArrayDecl"](varName, size, dataTypeName)

        varName = self.consumeToken("ID").tokenValue
        
        if self.match("EQ"):
            return self.parseInitializedDeclaration(varName, dataTypeName)
        
        self.consumeToken("SEMICOLON")
        return self.createVarDecl(varName, None, dataTypeName)

    def parseInitializedDeclaration(self, varName, typeName):
        self.consumeToken("EQ")
        initExpr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.createVarDecl(varName, initExpr, typeName)

    def parseFunction(self):
        dataTypeToken = self.consumeDatatype()
        name = self.consumeToken("ID").tokenValue
        self.consumeToken("LPAREN")
        args = self.consumeFuncArgs()
        self.consumeToken("RPAREN")
        if self.currentToken().tokenType == "SEMICOLON":
            self.consumeToken("SEMICOLON")
            body = None
        else:
            body = self.parseBlock()
        return self.astClasses["Function"](name, dataTypeToken.tokenValue, args, body)
    def consumeFuncArgs(self) -> list:
        args = []

        if self.peek().tokenType == "RPAREN":
            return args

        while True:
            if self.currentToken().tokenType == "RPAREN":
                return args
            dt = self.consumeDatatype().tokenValue
            id = self.consumeToken("ID").tokenValue

            args.append((dt, id))
            if self.currentToken().tokenType == "COMMA":
                self.consumeToken("COMMA")
            else:
                break

        return args


    def parseStatement(self):
        token = self.currentToken()
        if token.tokenType in self.statementParseMap:
            return self.statementParseMap[token.tokenType]()
        elif self.isDatatype(token):
            return self.parseDeclaration()
        else:
            expr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.astClasses["ExpressionStatement"](expr)

    def isDatatype(self, token):
        return token and (token.tokenType in self.datatypes or 
                         (token.tokenType == "ID" and 
                          (token.tokenValue in self.classNames or token.tokenValue == "string")))

    def consumeDatatype(self):
        token = self.currentToken()
        if self.isDatatype(token):
            return self.advance()
        raise SyntaxError(f"Expected datatype, got {token}")

    def parseReturn(self):
        self.consumeToken("RETURN")
        expr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.astClasses["Return"](expr)

    def parseExpression(self):
        return self.parseAssignment()

    def parseAssignment(self):
        node = self.parseBinaryExpression()
        if self.match("EQ"):
            self.consumeToken("EQ")
            right = self.parseAssignment()
            if node.__class__.__name__ in ("MemberAccess", "Var", "ArrayAccess"):
                return self.astClasses["Assign"](node, right)
            raise SyntaxError("Invalid left-hand side for assignment")
        return node

    def parseBinaryExpression(self, min_precedence=0):
        left = self.parseFactor()
        while True:
            token = self.currentToken()
            if not token:
                break
            token_type = token.tokenType
            if token_type not in self.op_precedences or self.op_precedences[token_type] < min_precedence:
                break
            op_prec = self.op_precedences[token_type]
            self.advance()
            right = self.parseBinaryExpression(op_prec + 1)
            op = token_type if token_type in self.language["operators"]["compMap"] else token.tokenValue
            left = self.astClasses["BinOp"](op, left, right)
        return left

    def parseFactor(self):
        token = self.currentToken()
        if token.tokenType == "NEW":
            self.consumeToken("NEW")
            classNameToken = self.consumeToken("ID")
            self.consumeToken("LPAREN")
            self.consumeToken("RPAREN")
            return self.astClasses["NewExpr"](classNameToken.tokenValue)
        if token.tokenType == "LBRACKET":
            return self.parseArrayLiteral()
        if token.tokenType in self.factorParseMap:
            return self.factorParseMap[token.tokenType]()
        raise SyntaxError(f"Unexpected token: {token}")

    def parseIdentifier(self):
        token = self.currentToken()
        if token.tokenType in ("ID", "SELF"):
            self.advance()
        else:
            raise SyntaxError(f"Expected identifier, got {token}")
        
        node = self.astClasses["Var"](token.tokenValue)
        return self.parseChainedAccess(node)
        
    def parseChainedAccess(self, node):
        while self.currentToken() and self.currentToken().tokenType in ("DOT", "LPAREN", "LBRACKET"):
            if self.match("DOT"):
                self.consumeToken("DOT")
                memberName = self.consumeToken("ID").tokenValue
                node = self.astClasses["MemberAccess"](node, memberName)
            elif self.match("LPAREN"):
                node = self.parseFunctionCallWithCallee(node)
            elif self.match("LBRACKET"):
                index = self.consumePairedTokens("LBRACKET", "RBRACKET", self.parseExpression)
                node = self.astClasses["ArrayAccess"](node, index)
        return node

    def parseFunctionCallWithCallee(self, callee):
        args = self.consumePairedTokens("LPAREN", "RPAREN", 
                                       lambda: self.parseDelimitedList("RPAREN", "COMMA", self.parseExpression))
        return self.astClasses["FunctionCall"](callee, args)

    def parseParenthesizedExpression(self):
        return self.consumePairedTokens("LPAREN", "RPAREN", self.parseExpression)

    def parseCondition(self):
        if self.match("LPAREN"):
            return self.consumePairedTokens("LPAREN", "RPAREN", self.parseExpression)
        return self.parseExpression()
        
    def parseControlFlow(self, keyword, nodeType, hasElse=False):
        self.consumeToken(keyword)
        condition = self.parseCondition()
        thenBody = self.parseBlock()
        elseBody = None
        
        if hasElse and self.match("ELSE"):
            self.consumeToken("ELSE")
            if nodeType == "If" and self.match("IF"):
                elseBody = [self.parseIf()]
            else:
                elseBody = self.parseBlock()
                
        return self.astClasses[nodeType](condition, thenBody, elseBody) if hasElse else self.astClasses[nodeType](condition, thenBody)

    def parseIf(self):
        return self.parseControlFlow("IF", "If", True)

    def parseWhile(self):
        return self.parseControlFlow("WHILE", "While")

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
        condition = self.parseCondition()
        self.consumeToken("SEMICOLON")
        return self.astClasses["DoWhile"](body, condition)

    def parseBlock(self):
        return self.consumePairedTokens("LBRACE", "RBRACE", self.parseBlockBody)
        
    def parseBlockBody(self):
        stmts = []
        while self.currentToken() and not self.match("RBRACE"):
            stmts.append(self.parseStatement())
        return stmts

    def parseArrayLiteral(self):
        elements = self.consumePairedTokens("LBRACKET", "RBRACKET", 
                                          lambda: self.parseDelimitedList("RBRACKET", "COMMA", self.parseExpression))
        return self.astClasses["ArrayLiteral"](elements)
