class Tool_Registry:
    _tools = {}

    @classmethod
    def register(cls, name, description, func):
        cls._tools[name] = {
            "description": description,
            "func": func
        }

    @classmethod
    def get(cls, name):
        return cls._tools.get(name)

    @classmethod
    def all(cls):
        return cls._tools


# Alias pour compatibilité
ToolRegistry = Tool_Registry