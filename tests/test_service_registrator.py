from typing import Protocol

import pytest
from serpentariumcore import (
    ConstructionFailed,
    MissingRequirements,
    ServiceContainer,
    ServiceRegistration,
)


def _test_service_registration_lazy_construction():
    ServiceContainer().clear()

    class IA(Protocol):
        def go_a(self): ...

    class IB(Protocol):
        def go_b(self): ...

    class IC(Protocol):
        def go_c(self): ...

    # Without lazy construction registration of IC would cause an Exception because
    # it requires services IA & IB which hasn't been registered yet.
    @ServiceRegistration(IC)
    class C:
        # Requires some services that implements both the IA and IB protocol
        def __init__(self, a: IA, b: IB):
            self.a: IA = a
            self.b: IB = b

        def go_c(self):
            return self.a.go_a() + " " + self.b.go_b() + " " + "And C as well!"

    @ServiceRegistration(IA)
    class A:
        # Requires no other service
        def __init__(self):
            pass

        def go_a(self):
            return "Go A!"

    @ServiceRegistration(IB)
    class B:
        # Requires some service that implements the IA protocol
        def __init__(self, a: IA):
            self.a = a

        def go_b(self):
            return "Go B!"

    assert ServiceContainer().sanity_check()


def test_service_registration_without_lazy_construction_crashes():
    ServiceContainer().clear()
    ServiceContainer(lazy_construction=False)

    class IA(Protocol):
        def go_a(self): ...

    class IB(Protocol):
        def go_b(self): ...

    class IC(Protocol):
        def go_c(self): ...

    # Without lazy construction registration of IC would cause an Exception because
    # it requires services IA & IB which hasn't been registered yet.
    with pytest.raises(MissingRequirements):

        @ServiceRegistration(IC)
        class C:
            # Requires some services that implements both the IA and IB protocol
            def __init__(self, a: IA, b: IB):
                self.a: IA = a
                self.b: IB = b
