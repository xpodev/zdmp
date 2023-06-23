from contextlib import contextmanager

from core.object_id import ObjectID
from zs.utils import SingletonMeta


class ObjectManager(metaclass=SingletonMeta):
    _objects: dict[object, ObjectID]
    _prefix: str | None
    _prefixed: int | None

    def __init__(self):
        self._objects = {}
        self._prefix = None
        self._prefixed = 0

    @contextmanager
    def scope(self, prefix: str = None):
        if prefix:
            prefix += '-'
        prefixed, self._prefixed = self._prefixed, 0
        prefix, self._prefix = self._prefix, prefix
        objects, self._objects = self._objects, self._objects.copy()
        try:
            yield
        finally:
            self._objects = objects
            self._prefixed = prefixed
            self._prefix = prefix

    def get_object_id(self, obj: object, strict: bool = False) -> ObjectID:
        try:
            return self._objects[obj]
        except KeyError:
            if strict:
                raise
            if self._prefix is None:
                result = self._objects[obj] = ObjectID(len(self._objects))
            else:
                result = self._objects[obj] = ObjectID(self._prefix + str(self._prefixed))
                self._prefixed += 1
            return result
