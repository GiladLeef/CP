tokens = [
    {"type": "COMMENT", "regex": r"//[^\n]*"},
    {"type": "CLASS", "regex": r"class"},
    {"type": "SELF", "regex": r"self"},
    {"type": "NEW", "regex": r"new"},
    {"type": "IF", "regex": r"if"},
    {"type": "ELSE", "regex": r"else"},
    {"type": "WHILE", "regex": r"while"},
    {"type": "FOR", "regex": r"for"},
    {"type": "DO", "regex": r"do"},
    {"type": "INT", "regex": r"int"},
    {"type": "FLOAT", "regex": r"float"},
    {"type": "CHAR", "regex": r"char"},
    {"type": "RETURN", "regex": r"return"},
    {"type": "FLOAT_NUMBER", "regex": r"\d+\.\d+"},
    {"type": "NUMBER", "regex": r"\d+"},
    {"type": "CHAR_LITERAL", "regex": r"'[^']'"},
    {"type": "ID", "regex": r"[a-zA-Z_][a-zA-Z0-9_]*"},
    {"type": "LPAREN", "regex": r"\("},
    {"type": "RPAREN", "regex": r"\)"},
    {"type": "LBRACE", "regex": r"\{"},
    {"type": "RBRACE", "regex": r"\}"},
    {"type": "SEMICOLON", "regex": r";"},
    {"type": "COMMA", "regex": r","},
    {"type": "PLUS", "regex": r"\+"},
    {"type": "MINUS", "regex": r"-"},
    {"type": "MULT", "regex": r"\*"},
    {"type": "DIV", "regex": r"/"},
    {"type": "MOD", "regex": r"%"},
    {"type": "BITAND", "regex": r"&"},
    {"type": "BITXOR", "regex": r"\^"},
    {"type": "BITOR", "regex": r"\|"},
    {"type": "LSHIFT", "regex": r"<<"},
    {"type": "RSHIFT", "regex": r">>"},
    {"type": "EQEQ", "regex": r"=="},
    {"type": "NEQ", "regex": r"!="},
    {"type": "LTE", "regex": r"<="},
    {"type": "GTE", "regex": r">="},
    {"type": "EQ", "regex": r"="},
    {"type": "LT", "regex": r"<"},
    {"type": "GT", "regex": r">"},
    {"type": "STRING", "regex": r'"[^"]*"'},
    {"type": "DOT", "regex": r"\."},
    {"type": "WS", "regex": r"\s+"}
]

operators = {
    "binOpMap": {
        "+": ["add", "fadd", "addtmp"],
        "-": ["sub", "fsub", "subtmp"],
        "*": ["mul", "fmul", "multmp"],
        "/": ["sdiv", "fdiv", "divtmp"],
        "%": ["srem", "srem", "remtmp"],
        "&": ["and_", "and_", "andtmp"],
        "^": ["xor", "xor", "xortmp"],
        "|": ["or_", "or_", "ortmp"],
        "<<": ["shl", "shl", "shltmp"],
        ">>": ["lshr", "lshr", "lshrtmp"]
    },
    "compMap": {
        "EQEQ": ["==", "==", "eqtmp"],
        "NEQ": ["!=", "!=", "neqtmp"],
        "LT": ["<", "<", "lttmp"],
        "GT": [">", ">", "gttmp"],
        "LTE": ["<=", "<=", "letmp"],
        "GTE": [">=", ">=", "getmp"]
    },
    "precedences": {
        "MULT": 4,
        "DIV": 4,
        "MOD": 4,
        "PLUS": 3,
        "MINUS": 3,
        "LSHIFT": 2,
        "RSHIFT": 2,
        "EQEQ": 2,
        "NEQ": 2,
        "LT": 2,
        "GT": 2,
        "LTE": 2,
        "GTE": 2,
        "BITAND": 1,
        "BITXOR": 1,
        "BITOR": 1
    }
}

datatypes = {
    "int": "IntType(32)",
    "float": "FloatType()",
    "char": "IntType(8)",
    "string": "PointerType(IntType(8))"
}

astnodes = [
    {"name": "Program", "fields": ["functions", "classes"]},
    {"name": "Function", "fields": ["name", "body"]},
    {"name": "MethodDecl", "fields": ["name", "parameters", "body", "className", "returnType"]},
    {"name": "Return", "fields": ["expr"]},
    {"name": "ExpressionStatement", "fields": ["expr"]},
    {"name": "VarDecl", "fields": ["name", "init", "datatypeName"]},
    {"name": "BinOp", "fields": ["op", "left", "right"]},
    {"name": "Num", "fields": ["value"]},
    {"name": "FloatNum", "fields": ["value"]},
    {"name": "Var", "fields": ["name"]},
    {"name": "String", "fields": ["value"]},
    {"name": "Char", "fields": ["value"]},
    {"name": "FunctionCall", "fields": ["callee", "args"]},
    {"name": "ClassDecl", "fields": ["name", "fields", "methods"]},
    {"name": "MemberAccess", "fields": ["objectExpr", "memberName"]},
    {"name": "Assign", "fields": ["left", "right"]},
    {"name": "If", "fields": ["condition", "thenBranch", "elseBranch"]},
    {"name": "While", "fields": ["condition", "body"]},
    {"name": "For", "fields": ["init", "condition", "increment", "body"]},
    {"name": "DoWhile", "fields": ["body", "condition"]},
    {"name": "NewExpr", "fields": ["className"]}
]

statementParseMap = {
    "RETURN": "parseReturn",
    "IF": "parseIf",
    "WHILE": "parseWhile",
    "FOR": "parseFor",
    "DO": "parseDoWhile",
    "SELF": "parseIdentifier"
}

factorParseMap = {
    "NUMBER": {"method": "parseLiteral", "args": ["NUMBER", "Num"]},
    "FLOAT_NUMBER": {"method": "parseLiteral", "args": ["FLOAT_NUMBER", "FloatNum"]},
    "STRING": {"method": "parseLiteral", "args": ["STRING", "String"]},
    "CHAR_LITERAL": {"method": "parseLiteral", "args": ["CHAR_LITERAL", "Char"]},
    "ID": "parseIdentifier",
    "SELF": "parseIdentifier",
    "LPAREN": "parseParenthesizedExpression"
}

language = {
    "tokens": tokens,
    "operators": operators,
    "datatypes": datatypes,
    "astnodes": astnodes,
    "statementParseMap": statementParseMap,
    "factorParseMap": factorParseMap
}