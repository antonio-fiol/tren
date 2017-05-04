def ChangeMonitor(cls):
    _sentinel = object()
    old_setattr = getattr(cls, '__setattr__', None)
    def __setattr__(self, name, value):
        old = getattr(self, name, _sentinel)
        if old is not _sentinel and old != value and name not in ("t_ultima_actualizacion_espacio"):
            print("Old {0} = {1!r}, new {0} = {2!r}".format(name, old, value))
        if old_setattr:
            old_setattr(self, name, value)
        else:
            # Old-style class
            self.__dict__[name] = value

    cls.__setattr__ = __setattr__

    return cls
