import re
from tokens import Token
class Lexer:
    def __init__(self, tokens):
        self.tokens = [(tokenType, re.compile(pattern)) for tokenType, pattern in tokens]

    def lex(self, characters):
        currPos = 0
        tokenList = []
        while currPos < len(characters):
            matchFound = None
            for tokenType, regex in self.tokens:
                matchFound = regex.match(characters, currPos)
                if matchFound:
                    text = matchFound.group(0)
                    if tokenType == "COMMENT":
                        currPos = matchFound.end(0)
                        break
                    if tokenType != "WS":
                        if tokenType == "STRING" or tokenType == "CHAR_LITERAL":
                            text = text[1:-1]
                        tokenList.append(Token(tokenType, text))
                    currPos = matchFound.end(0)
                    break
            if not matchFound:
                raise SyntaxError("Illegal character: " + characters[currPos])
        return tokenList
