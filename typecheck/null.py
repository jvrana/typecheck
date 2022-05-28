class NullType:
    class __Null:
        def __str__(self):
            return "Null"

    instance = None

    def __init__(self):
        if not NullType.instance:
            NullType.instance = NullType.__Null()

    def __bool__(self):
        return False

    def __str__(self):
        return "Null"

    def __repr__(self):
        return "Null"


Null = NullType()
