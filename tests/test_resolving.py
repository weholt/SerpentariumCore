from typing import Protocol

import pytest
from serpentariumcore import MissingRequirements, ServiceContainer


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
    ServiceContainer().register(IC, C)
    # Not registering the IB service, which service C requires
    with pytest.raises(MissingRequirements):
        ServiceContainer().resolve(IC)


def test_dynamic_object_construction_lazy_construction():
    ServiceContainer().clear()
    ServiceContainer().register(IA, A)
    ServiceContainer().register(IC, C)
    ServiceContainer().register(IB, B)
    # Registering IC before IB, even if IB requires IC to be registered
    # Lazy constructions should not cause this to
    assert ServiceContainer().resolve(IC) != None


def test_sanity_check_success():
    ServiceContainer().clear()
    ServiceContainer().register(IA, A)
    ServiceContainer().register(IC, C)
    ServiceContainer().register(IB, B)
    assert ServiceContainer().sanity_check() == True


def test_sanity_check_fails():
    ServiceContainer().clear()
    ServiceContainer().register(IC, C)
    ServiceContainer().register(IB, B)
    with pytest.raises(MissingRequirements):
        assert ServiceContainer().sanity_check()
