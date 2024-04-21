import sys
from typing import get_args
import inspect
import uuid
from dataclasses import dataclass, field
from typing import ClassVar, Any, List, TypeVar, Protocol


def print_classes(parent_class: Any) -> dict[Any, Any]:
    result = {}
    for _, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and issubclass(obj, parent_class):
            if hasattr(obj, "target"):
                if target := obj.target():
                    result[target] = obj

    import pprint

    pprint.pprint(result)
    return result

class IA(Protocol):

    def go_a(self):
        print("Go IA!")

class IB(Protocol):

    def go_b(self):
        print("Go IB!")

class A:
    def __init__(self):
        pass

    def go_a(self):
        print("Go A!")

class B:
    def __init__(self):
        pass

    def go_b(self):
        print("Go B!")


class C:
    def __init__(self, a: IA, b: IB):
        self.a: IA = a
        self.b: IB = b

    def go(self):
        self.a.go_a()
        self.b.go_b()


def test_type_args():
    reg = {IA: A(), IB: B()}

    d =inspect.getfullargspec(C.__init__)
    print(dir(d))
    reqs = {k:v for k,v in d.annotations.items()}
    params = {}
    for k,v in reqs.items():
        if v in reg:
            params[k] = reg[v]
    c = C(**params)
    c.go()



