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
import re

class AstFactory:
    def __init__(self, language):
        self.language = language
        self.astClasses = {}
        self.createAstClasses()

    def createAstClasses(self):
        for node in self.language["astnodes"]:
            self.astClasses[node["name"]] = self.createAstClass(node["name"], node["fields"])

    def createAstClass(self, name, fields):
        def init(self, *args):
            if len(args) != len(fields):
                raise TypeError("Expected %d args" % len(fields))
            for f, a in zip(fields, args):
                setattr(self, f, a)

        def repr(self):
            return name + "(" + ", ".join(str(getattr(self, f)) for f in fields) + ")"

        return type(name, (object,), {"__init__": init, "__repr__": repr})

class Token:
    def __init__(self, tokenType, tokenValue):
        self.tokenType = tokenType
        self.tokenValue = tokenValue

    def __repr__(self):
        return "Token(%s, %s)" % (self.tokenType, self.tokenValue)

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
