from typing import Protocol

import pytest
from serpentariumcore import (
    ServiceContainer,
    ServiceRequiresOtherServiceWithIdenticalProtocol,
    multi_register_as,
    register_as,
    resolve_multi,
)


def test_multi_service_registration_lazy_construction():
    ServiceContainer().clear()

    class IB(Protocol):
        def generate(self) -> int: ...

    class IA(Protocol):
        def generate(self) -> int: ...

    @multi_register_as(IA)
    class C:
        # Requires some services that implements both the IA and IB protocol

        def generate(self):
            return 1

    @multi_register_as(IA)
    class A:
        def generate(self):
            return 2

    @register_as(IB)
    class D:
        def generate(self):
            return 42

    @multi_register_as(IA)
    class B:
        # Requires some service that implements the IB protocol
        def __init__(self, b: IB):
            self.b = b

        def generate(self):
            return self.b.generate() + 3

    assert ServiceContainer().sanity_check()
    services = list(resolve_multi(IA))
    result = sum([s.generate() for s in services])
    assert result == 48


def test_multi_service_registration_crashes_if_one_multi_service_requires_another_multi_service():
    ServiceContainer().clear()

    class IB(Protocol):
        def generate(self) -> int: ...

    class IA(Protocol):
        def generate(self) -> int: ...

    @multi_register_as(IA)
    class C:
        def generate(self):
            return 1

    @multi_register_as(IA)
    class A:
        def generate(self):
            return 2

    @register_as(IB)
    class D:
        def generate(self):
            return 42

    with pytest.raises(ServiceRequiresOtherServiceWithIdenticalProtocol):

        @multi_register_as(IA)
        class B:
            # Requires some service that implements the IB protocol
            def __init__(self, b: IB, c: IA): ...

            def generate(self):
                pass


def test_multi_service_over_and_over_does_not_give_duplicates():
    ServiceContainer().clear()

    class IB(Protocol):
        def generate(self) -> int: ...

    @multi_register_as(IB)
    class C:
        def generate(self):
            return 1

    @multi_register_as(IB)
    class A:
        def generate(self):
            return 2

    @multi_register_as(IB)
    @multi_register_as(IB)
    class D:
        def generate(self):
            return 42
