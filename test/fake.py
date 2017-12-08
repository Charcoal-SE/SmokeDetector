class Fake:
    def __init__(self, d, spec=None):
        for key, value in d.items():
            if isinstance(value, dict):
                setattr(self, key, Fake(value))
            else:
                setattr(self, key, value)

        if spec:
            self.__class__ = spec
