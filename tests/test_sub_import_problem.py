from serpentariumcore import multi_register_as, resolve_multi

from .mod1 import TheProtocol


@multi_register_as(TheProtocol)
class Tutor:
    def speak(self, msg: str) -> str:
        return f"Says '{msg}"


def test_assert_no_multiregistration():
    from .mod1 import TheProtocol

    assert len(list(resolve_multi(TheProtocol))) == 2
