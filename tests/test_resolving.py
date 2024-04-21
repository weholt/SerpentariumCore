from typing import Protocol
import pytest

from serpentariumcore import ServiceContainer, MissingRequirements


class IA(Protocol):

    def go_a(self): ...


class IB(Protocol):

    def go_b(self): ...


class IC(Protocol):

    def go_c(self): ...


class A:
    # Requires no other service
    def __init__(self):
        pass

    def go_a(self):
        return "Go A!"


class B:
    # Requires some service that implements the IA protocol
    def __init__(self, a: IA):
        self.a = a

    def go_b(self):
        return "Go B!"


class C:
    # Requires some services that implements both the IA and IB protocol
    def __init__(self, a: IA, b: IB):
        self.a: IA = a
        self.b: IB = b

    def go_c(self):
        return self.a.go_a() + " " + self.b.go_b() + " " + "And C as well!"


def test_dynamic_object_construction():
    ServiceContainer().clear()
    ServiceContainer().register(IA, A)
    ServiceContainer().register(IB, B)
    ServiceContainer().register(IC, C)
    if c := ServiceContainer().resolve(IC):
        assert c.go_c() is not None


def test_dynamic_object_construction_missing_requirement():
    ServiceContainer().clear()
    ServiceContainer().register(IA, A)
    # Not registering the IB service, which service C requires
    with pytest.raises(MissingRequirements):
        ServiceContainer().register(IC, C)
    try:
        ServiceContainer().register(IC, C)
    except MissingRequirements as ex:
        print(ex)
