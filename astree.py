class AstFactory:
    def __init__(self, langDef):
        self.langDef = langDef
        self.astClasses = {}
        self.createAstClasses()

    def createAstClasses(self):
        for node in self.langDef["astNodes"]:
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
