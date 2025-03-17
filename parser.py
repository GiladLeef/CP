from tokens import Token
class Parser:
    def __init__(self, tokens, astClasses, langDef):
        self.tokens = tokens
        self.pos = 0
        self.astClasses = astClasses
        self.langDef = langDef
        self.classNames = set()
        self.statementParseMap = {}
        for key, funcName in langDef["statementParseMap"].items():
            self.statementParseMap[key] = getattr(self, funcName)
        self.factorParseMap = {}
        for key, value in langDef["factorParseMap"].items():
            if isinstance(value, dict):
                method = getattr(self, value["method"])
                args = value["args"]
                self.factorParseMap[key] = (lambda m=method, a=args: m(*a))
            else:
                self.factorParseMap[key] = getattr(self, value)
    def currentToken(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    def consumeToken(self, tokenType):
        token = self.currentToken()
        if token and token.tokenType == tokenType:
            self.pos += 1
            return token
        raise SyntaxError("Expected token " + tokenType + ", got " + str(token))
    def parseLiteral(self, tokenType, astName):
        token = self.consumeToken(tokenType)
        return self.astClasses[astName](token.tokenValue)
    def parseProgram(self):
        functions = []
        classes = []
        while self.currentToken() is not None:
            if self.currentToken().tokenType == "CLASS":
                classDecl = self.parseClassDeclaration()
                classes.append(classDecl)
                self.classNames.add(classDecl.name)
            elif self.currentToken().tokenType in ("INT", "FLOAT", "CHAR", "ID") and (self.currentToken().tokenType != "ID" or self.currentToken().tokenValue != "class"):
                functions.append(self.parseFunction())
            else:
                self.consumeToken(self.currentToken().tokenType)
        return self.astClasses["Program"](functions, classes)
    def parseClassDeclaration(self):
        self.consumeToken("CLASS")
        className = self.consumeToken("ID").tokenValue
        self.consumeToken("LBRACE")
        fields = []
        methods = []
        while self.currentToken() and self.currentToken().tokenType != "RBRACE":
            member = self.parseClassMember()
            if member.__class__.__name__ == "MethodDecl":
                member.className = className
                methods.append(member)
            else:
                fields.append(member)
        self.consumeToken("RBRACE")
        return self.astClasses["ClassDecl"](className, fields, methods)
    def parseClassMember(self):
        dataTypeToken = self.consumeDatatype()
        nameToken = self.consumeToken("ID")
        if self.currentToken() and self.currentToken().tokenType == "LPAREN":
            return self.parseMethodDeclaration(dataTypeToken, nameToken)
        else:
            self.consumeToken("SEMICOLON")
            return self.astClasses["VarDecl"](nameToken.tokenValue, None, dataTypeToken.tokenValue)
    def parseMethodDeclaration(self, returnTypeToken, nameToken):
        methodName = nameToken.tokenValue
        self.consumeToken("LPAREN")
        params = []
        if self.currentToken() and self.currentToken().tokenType != "RPAREN":
            params.append(self.parseParameter())
            while self.currentToken() and self.currentToken().tokenType == "COMMA":
                self.consumeToken("COMMA")
                params.append(self.parseParameter())
        self.consumeToken("RPAREN")
        body = self.parseBlock()
        return self.astClasses["MethodDecl"](methodName, params, body, None)
    def parseParameter(self):
        dataTypeToken = self.consumeDatatype()
        idToken = self.consumeToken("ID")
        return self.astClasses["VarDecl"](idToken.tokenValue, None, dataTypeToken.tokenValue)
    def parseDeclaration(self):
        dataTypeToken = self.consumeDatatype()
        varName = self.consumeToken("ID").tokenValue
        dataTypeName = dataTypeToken.tokenValue
        if self.currentToken() and self.currentToken().tokenType == "EQ":
            self.consumeToken("EQ")
            initExpr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.astClasses["VarDecl"](varName, initExpr, dataTypeName)
        self.consumeToken("SEMICOLON")
        return self.astClasses["VarDecl"](varName, None, dataTypeName)
    def parseFunction(self):
        dataTypeToken = self.consumeDatatype()
        name = self.consumeToken("ID").tokenValue
        self.consumeToken("LPAREN")
        self.consumeToken("RPAREN")
        self.consumeToken("LBRACE")
        body = []
        while self.currentToken() and self.currentToken().tokenType != "RBRACE":
            body.append(self.parseStatement())
        self.consumeToken("RBRACE")
        return self.astClasses["Function"](name, body)
    def parseStatement(self):
        token = self.currentToken()
        if token.tokenType in self.statementParseMap:
            return self.statementParseMap[token.tokenType]()
        elif token.tokenType in ("INT", "FLOAT", "CHAR") or (token.tokenType == "ID" and (token.tokenValue in self.classNames or token.tokenValue == "string")):
            return self.parseDeclaration()
        else:
            expr = self.parseExpression()
            self.consumeToken("SEMICOLON")
            return self.astClasses["ExpressionStatement"](expr)
    def consumeDatatype(self):
        token = self.currentToken()
        if token.tokenType in ("INT", "FLOAT", "CHAR") or (token.tokenType == "ID" and (token.tokenValue in self.classNames or token.tokenValue == "string")):
            self.pos += 1
            return token
        raise SyntaxError("Expected datatype, got " + str(token))
    def parseReturn(self):
        self.consumeToken("RETURN")
        expr = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.astClasses["Return"](expr)
    def parseExpression(self):
        return self.parseAssignment()
    def parseAssignment(self):
        node = self.parseComparison()
        if self.currentToken() and self.currentToken().tokenType == "EQ":
            self.consumeToken("EQ")
            right = self.parseAssignment()
            if node.__class__.__name__ in ("MemberAccess", "Var"):
                return self.astClasses["Assign"](node, right)
            raise SyntaxError("Invalid left-hand side for assignment")
        return node
    def parseBinary(self, lowerFn, ops, useTokenValue=True):
        node = lowerFn()
        while self.currentToken() and self.currentToken().tokenType in ops:
            opToken = self.consumeToken(self.currentToken().tokenType)
            op = opToken.tokenValue if useTokenValue else opToken.tokenType
            node = self.astClasses["BinOp"](op, node, lowerFn())
        return node
    def parseComparison(self):
        return self.parseBinary(self.parseAdditiveExpression, {"EQEQ", "NEQ", "LT", "GT", "LTE", "GTE"}, False)
    def parseAdditiveExpression(self):
        return self.parseBinary(self.parseMultiplicativeExpression, {"PLUS", "MINUS"})
    def parseMultiplicativeExpression(self):
        return self.parseBinary(self.parseFactor, {"MULT", "DIV", "MOD"})
    def parseFactor(self):
        token = self.currentToken()
        if token.tokenType == "NEW":
            self.consumeToken("NEW")
            classNameToken = self.consumeToken("ID")
            self.consumeToken("LPAREN")
            self.consumeToken("RPAREN")
            return self.astClasses["NewExpr"](classNameToken.tokenValue)
        if token.tokenType in self.factorParseMap:
            return self.factorParseMap[token.tokenType]()
        raise SyntaxError("Unexpected token: " + str(token))
    def parseIdentifier(self):
        token = self.currentToken()
        if token.tokenType in ("ID", "SELF"):
            self.pos += 1  
        else:
            raise SyntaxError("Expected identifier, got " + str(token))
        node = self.astClasses["Var"](token.tokenValue)
        while self.currentToken() and self.currentToken().tokenType in ("DOT", "LPAREN"):
            if self.currentToken().tokenType == "DOT":
                self.consumeToken("DOT")
                memberName = self.consumeToken("ID").tokenValue
                node = self.astClasses["MemberAccess"](node, memberName)
            elif self.currentToken().tokenType == "LPAREN":
                node = self.parseFunctionCallWithCallee(node)
        return node

    def parseFunctionCallWithCallee(self, callee):
        self.consumeToken("LPAREN")
        args = []
        if self.currentToken() and self.currentToken().tokenType != "RPAREN":
            args.append(self.parseExpression())
            while self.currentToken() and self.currentToken().tokenType == "COMMA":
                self.consumeToken("COMMA")
                args.append(self.parseExpression())
        self.consumeToken("RPAREN")
        return self.astClasses["FunctionCall"](callee, args)
    def parseParenthesizedExpression(self):
        self.consumeToken("LPAREN")
        node = self.parseExpression()
        self.consumeToken("RPAREN")
        return node
    def parseIf(self):
        self.consumeToken("IF")
        if self.currentToken().tokenType == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        thenBranch = self.parseBlock()
        elseBranch = None
        if self.currentToken() and self.currentToken().tokenType == "ELSE":
            self.consumeToken("ELSE")
            elseBranch = [self.parseIf()] if self.currentToken() and self.currentToken().tokenType == "IF" else self.parseBlock()
        return self.astClasses["If"](condition, thenBranch, elseBranch)
    def parseWhile(self):
        self.consumeToken("WHILE")
        if self.currentToken().tokenType == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        body = self.parseBlock()
        return self.astClasses["While"](condition, body)
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
        if self.currentToken().tokenType == "LPAREN":
            self.consumeToken("LPAREN")
            condition = self.parseExpression()
            self.consumeToken("RPAREN")
        else:
            condition = self.parseExpression()
        self.consumeToken("SEMICOLON")
        return self.astClasses["DoWhile"](body, condition)
    def parseBlock(self):
        self.consumeToken("LBRACE")
        stmts = []
        while self.currentToken() and self.currentToken().tokenType != "RBRACE":
            stmts.append(self.parseStatement())
        self.consumeToken("RBRACE")
        return stmts