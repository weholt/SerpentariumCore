from typing import Callable, Protocol, Tuple

import pytest

from serpentariumcore import ServiceAlreadyRegistered, ServiceArgument, ServiceContainer, ServiceRegistration, register_as, resolve


class TheTalkingProtocol(Protocol):
    def speak(self, sentence) -> str:
        ...


class Speaker:
    def speak(self, sentence) -> str:
        return f"The speaker says '{sentence}'."


class Teacher:
    def speak(self, sentence) -> str:
        return f"The teacher screams '{sentence}'."


class Substitute:
    def speak(self, sentence) -> str:
        return f"The substitute mumbles '{sentence}'."


class DummyWrapping(ServiceArgument):
    pass


def test_teacher_using_both_shortcuts():
    ServiceContainer().clear()

    @register_as(TheTalkingProtocol)
    class HeadMaster:
        def speak(self, sentence) -> str:
            return f"The headmaster whispers '{sentence}'."

    if person := resolve(TheTalkingProtocol):
        assert person.speak(sentence="The dog sits on a mat") == "The headmaster whispers 'The dog sits on a mat'."


def test_teacher_using_shortcut():
    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Teacher())

    if person := resolve(TheTalkingProtocol):
        assert person.speak(sentence="The dog sits on a mat") == "The teacher screams 'The dog sits on a mat'."


def test_teacher():
    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Teacher())

    if person := ServiceContainer().resolve(TheTalkingProtocol):
        assert person.speak(sentence="The dog sits on a mat") == "The teacher screams 'The dog sits on a mat'."


def test_speaker():
    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Speaker())

    if person := ServiceContainer().resolve(TheTalkingProtocol):
        assert person.speak(sentence="The dog sits on a mat") == "The speaker says 'The dog sits on a mat'."


def test_namespace():
    s = ServiceContainer()
    s.clear()
    assert s.namespace == "default"
    s.set_namespace("test")
    assert s.namespace == "test"
    # assert s.__previous_namespace == "default"
    with ServiceContainer(namespace="prod") as s2:
        assert s2.namespace == "prod"
    assert s.namespace == "test"


def test_resolving_namespaces():
    s = ServiceContainer()
    s.clear()
    s.register(TheTalkingProtocol, Teacher())
    s.register(TheTalkingProtocol, Speaker(), namespace="test")
    if person := ServiceContainer().resolve(TheTalkingProtocol):
        assert person.speak(sentence="The dog sits on a mat") == "The teacher screams 'The dog sits on a mat'."
    with ServiceContainer("test") as s2:
        if person := ServiceContainer().resolve(TheTalkingProtocol):
            assert person.speak(sentence="The dog sits on a mat") == "The speaker says 'The dog sits on a mat'."


def test_registration_with_kwargs():
    ServiceContainer().clear()

    @ServiceRegistration(TheTalkingProtocol).with_arguments(ServiceArgument(**{"joke": "A barber, a developer and a mechanic walks into a bar"}))
    class Comedian:
        def __init__(self, *args, **kwargs):
            self.joke = kwargs.get("joke", "Two donkeys walk into a bar")

        def speak(self, sentence) -> str:
            return f"The comedian laughs and says '{self.joke} ... but {sentence}'."

    if person := ServiceContainer().resolve(TheTalkingProtocol):
        assert (
            person.speak(sentence="The dog sits on a mat") == "The comedian laughs and says 'A barber, a developer and a mechanic walks into a bar ... but The dog sits on a mat'."
        )


def test_registration_with_kwargs_and_namespace():
    ServiceContainer().clear()

    @ServiceRegistration(TheTalkingProtocol, namespace="jokes").with_arguments(ServiceArgument(**{"joke": "A barber, a developer and a mechanic walks into a bar"}))
    class Comedian:
        def __init__(self, *args, **kwargs):
            self.joke = kwargs.get("joke", "Two donkeys walk into a bar")

        def speak(self, sentence) -> str:
            return f"The comedian laughs and says '{self.joke} ... but {sentence}'."

    if person := ServiceContainer().resolve(TheTalkingProtocol, namespace="jokes"):
        assert (
            person.speak(sentence="The dog sits on a mat") == "The comedian laughs and says 'A barber, a developer and a mechanic walks into a bar ... but The dog sits on a mat'."
        )


def test_registration_with_same_instance_different_namespace():
    ServiceContainer().clear()

    class LoggingBase(Protocol):
        def log(self, msg: str) -> None:
            ...

    @ServiceRegistration(LoggingBase)
    class LoggingCritical:
        def log(self, msg: str) -> Tuple[str, str]:
            return ("CRITICAL", msg)

    @ServiceRegistration(LoggingBase, namespace="debug")
    class LoggingDebug:
        def log(self, msg: str) -> Tuple[str, str]:
            return ("DEBUG", msg)

    if logger := ServiceContainer().resolve(LoggingBase):
        level, _ = logger.log(msg="A critical message")
        assert level == "CRITICAL"

    if logger := ServiceContainer().resolve(LoggingBase, "debug"):
        level, _ = logger.log(msg="A critical message")
        assert level == "DEBUG"


def test_registration_with_same_instance_custom_func():
    ServiceContainer().clear()

    class FancyLoggingBase(Protocol):
        def log(self, msg: str, func: Callable[[str], str]) -> str:
            ...

    class LoggingTakingFunc:
        def __init__(self, func: Callable[[str], str]) -> None:
            self.func = func

        def log(self, msg: str) -> str:
            return self.func(msg)

    def log_critical(msg: str) -> str:
        return f"CRITICAL: {msg}"

    def log_debug(msg: str) -> str:
        return f"DEBUG: {msg}"

    ServiceContainer().register(FancyLoggingBase, LoggingTakingFunc(func=log_critical))
    ServiceContainer().register(FancyLoggingBase, LoggingTakingFunc(func=log_debug), namespace="debug")

    if critical_logger := ServiceContainer().resolve(FancyLoggingBase):
        assert "CRITICAL" in critical_logger.log(msg="Should be critical")

    if debug_logger := ServiceContainer().resolve(FancyLoggingBase, namespace="debug"):
        assert "DEBUG" in debug_logger.log(msg="Should be debug")

    # Simulate Django settings for test and prod
    class test_settings:
        DEBUG = True

    class prod_settings:
        DEBUG = False

    settings = test_settings()
    if clueless_logger := ServiceContainer().resolve(FancyLoggingBase, namespace=settings.DEBUG and "debug"):
        assert "DEBUG" in clueless_logger.log(msg="Should be debug")

    settings = prod_settings()
    if clueless_logger := ServiceContainer().resolve(FancyLoggingBase, namespace=settings.DEBUG and "debug" or None):
        assert "CRITICAL" in clueless_logger.log(msg="Should be critical")


def test_namespace_resolver():
    ServiceContainer().clear()

    class FancyLoggingBase(Protocol):
        def log(self, msg: str, func: Callable[[str], str]) -> str:
            ...

    class LoggingTakingFunc:
        def __init__(self, func: Callable[[str], str]) -> None:
            self.func = func

        def log(self, msg: str) -> str:
            return self.func(msg)

    def log_critical(msg: str) -> str:
        return f"CRITICAL: {msg}"

    def log_debug(msg: str) -> str:
        return f"DEBUG: {msg}"

    ServiceContainer().register(FancyLoggingBase, LoggingTakingFunc(func=log_critical))
    ServiceContainer().register(FancyLoggingBase, LoggingTakingFunc(func=log_debug), namespace="debug")

    # Simulate Django settings for test and prod
    class Settings:
        DEBUG = True

    settings = Settings()

    def resolve_namespace():
        return settings.DEBUG and "debug" or None

    ServiceContainer().set_namespace_resolver(resolve_namespace)
    if clueless_logger := ServiceContainer().resolve(FancyLoggingBase):
        assert "DEBUG" in clueless_logger.log(msg="Should be debug")

    settings.DEBUG = False
    if clueless_logger := ServiceContainer().resolve(FancyLoggingBase):
        assert "CRITICAL" in clueless_logger.log(msg="Should be critical")


def test_wrapper():
    ServiceContainer().clear()

    class FancyLoggingBase(Protocol):
        def log(self, msg: str, func: Callable[[str], str]) -> str:
            ...

    class ExtraArguments(ServiceArgument):
        def unwrap(self):
            self.kwargs.update({"name": "Thomas"})
            return super().unwrap()

    @ServiceRegistration(FancyLoggingBase).with_arguments(ExtraArguments(**{"saying": "Poof goes the dragon!"}))
    class Logging:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def log(self, msg: str) -> str:
            return f"{msg} + {self.kwargs}"

    if logger := ServiceContainer().resolve(FancyLoggingBase):
        assert logger.log("Hello Ma!") == "Hello Ma! + {'saying': 'Poof goes the dragon!', 'name': 'Thomas'}"


def test_duplicate_registration():
    ServiceContainer().setconfig({"raise_exception_on_double_registrations": True})
    ServiceContainer().register(TheTalkingProtocol, Teacher())
    with pytest.raises(ServiceAlreadyRegistered):
        ServiceContainer().register(TheTalkingProtocol, Teacher())


def test_replace_registration():
    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Teacher())
    ServiceContainer().replace(TheTalkingProtocol, Substitute())
    if srv := ServiceContainer().resolve(TheTalkingProtocol):
        assert srv.speak("Dog") == "The substitute mumbles 'Dog'."


def test_remove_registration():
    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Teacher())
    ServiceContainer().remove(TheTalkingProtocol)
    assert ServiceContainer().resolve(TheTalkingProtocol) == None


def test_namespace_resolver_namespace_property():
    def resolver():
        return "test"

    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Teacher(), namespace="test")
    ServiceContainer().set_namespace_resolver(resolver)
    assert isinstance(ServiceContainer().resolve(TheTalkingProtocol), Teacher)
    assert ServiceContainer().namespace == "test"


def test_clear_namespace_resolver():
    def resolver():
        return "test"

    ServiceContainer().clear()
    ServiceContainer().register(TheTalkingProtocol, Teacher(), namespace="test")
    ServiceContainer().set_namespace_resolver(resolver)
    assert isinstance(ServiceContainer().resolve(TheTalkingProtocol), Teacher)
    assert ServiceContainer().namespace == "test"
    ServiceContainer().clear_namespace_resolver()
    assert ServiceContainer().namespace == "default"


def test_remove_registration_with_instance():
    ServiceContainer().clear()

    class A:
        pass

    class B(A):
        pass

    ServiceContainer().register(A, B())
    ServiceContainer().remove(A())
    assert ServiceContainer().resolve(A) == None


def test_wrapper_service_base():
    ServiceContainer().clear()

    class IA(Protocol):
        def speak(self):
            ...

    class A:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def speak(self):
            return f"Here are kwargs: {self.kwargs}"

    ServiceContainer().register(IA, ServiceArgument(some="foobar", variable="something").for_service(A))
    if res := ServiceContainer().resolve(IA):
        assert res.speak() != None


def test_wrapper_service_base_with_dependencies():
    ServiceContainer().clear()

    class IB(Protocol):
        def howl(self):
            ...

    class B:
        def howl(self) -> str:
            return "YAHOOO!"

    class IA(Protocol):
        def speak(self) -> str:
            ...

    class A:
        def __init__(self, b: IB, **kwargs):
            self.b = b
            self.kwargs = kwargs

        def speak(self) -> str:
            return f"Here are kwargs: {self.kwargs} and a word from B: {self.b.howl()}"

    ServiceContainer().register(IB, B)
    ServiceContainer().register(IA, ServiceArgument(some="foobar", variable="something").for_service(A))
    if res := ServiceContainer().resolve(IA):
        spoken: str = res.speak()
        # Here we test to see if both the foobar supplied as extra argument
        # and the data from the required service IB are in the response
        assert "foobar" in spoken and "YAHOO" in spoken
