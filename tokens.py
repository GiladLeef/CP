class Token:
    def __init__(self, tokenType, tokenValue):
        self.tokenType = tokenType
        self.tokenValue = tokenValue

    def __repr__(self):
        return "Token(%s, %s)" % (self.tokenType, self.tokenValue)
