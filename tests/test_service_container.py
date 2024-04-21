from typing import Callable, Protocol, Tuple

from serpentariumcore.service_container import ServiceContainer, ServiceRegistrator, WrapperService


class TheTalkingProtocol(Protocol):
    def speak(self, sentence) -> str: ...


class Speaker:
    def speak(self, sentence) -> str:
        return f"The speaker says '{sentence}'."


class Teacher:
    def speak(self, sentence) -> str:
        return f"The teacher screams '{sentence}'."


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


def test_registrator_with_kwargs():
    ServiceContainer().clear()

    @ServiceRegistrator(TheTalkingProtocol, **{"joke": "A barber, a developer and a mechanic walks into a bar"})
    class Comedian:

        def __init__(self, **kwargs):
            self.joke = kwargs.get("joke", "Two donkeys walk into a bar")

        def speak(self, sentence) -> str:
            return f"The comedian laughs and says '{self.joke} ... but {sentence}'."

    if person := ServiceContainer().resolve(TheTalkingProtocol):
        assert (
            person.speak(sentence="The dog sits on a mat") == "The comedian laughs and says 'A barber, a developer and a mechanic walks into a bar ... but The dog sits on a mat'."
        )


def test_registrator_with_kwargs_and_namespace():
    @ServiceRegistrator(TheTalkingProtocol, namespace="jokes", **{"joke": "A barber, a developer and a mechanic walks into a bar"})
    class Comedian:

        def __init__(self, **kwargs):
            self.joke = kwargs.get("joke", "Two donkeys walk into a bar")

        def speak(self, sentence) -> str:
            return f"The comedian laughs and says '{self.joke} ... but {sentence}'."

    if person := ServiceContainer().resolve(TheTalkingProtocol, namespace="jokes"):
        assert (
            person.speak(sentence="The dog sits on a mat") == "The comedian laughs and says 'A barber, a developer and a mechanic walks into a bar ... but The dog sits on a mat'."
        )


def test_registrator_with_same_instance_different_namespace():

    ServiceContainer().clear()

    class LoggingBase(Protocol):
        def log(self, msg: str) -> None: ...

    @ServiceRegistrator(LoggingBase)
    class LoggingCritical:
        def log(self, msg: str) -> Tuple[str, str]:
            return ("CRITICAL", msg)

    @ServiceRegistrator(LoggingBase, namespace="debug")
    class LoggingDebug:
        def log(self, msg: str) -> Tuple[str, str]:
            return ("DEBUG", msg)

    with ServiceContainer() as s:
        if logger := s.resolve(LoggingBase):
            level, _ = logger.log(msg="A critical message")
            assert level == "CRITICAL"

    with ServiceContainer("debug") as s:
        if logger := s.resolve(LoggingBase):
            level, _ = logger.log(msg="A critical message")
            assert level == "DEBUG"


def test_registrator_with_same_instance_custom_func():

    ServiceContainer().clear()

    class FancyLoggingBase(Protocol):
        def log(self, msg: str, func: Callable[[str], str]) -> str: ...

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
        def log(self, msg: str, func: Callable[[str], str]) -> str: ...

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
        def log(self, msg: str, func: Callable[[str], str]) -> str: ...

    class PresentWrapping(WrapperService):

        def unwrap(self):
            self.kwargs.update({"name": "Thomas"})
            self.args += (
                "foo",
                "bar",
            )
            return super().unwrap()

    @ServiceRegistrator(FancyLoggingBase, None, *(1, 2, 3), **{"saying": "Poof goes the dragon!"}).wrap(PresentWrapping)
    class Logging:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        def log(self, msg: str) -> str:
            return f"{msg} + {self.args} + {self.kwargs}"

    if logger := ServiceContainer().resolve(FancyLoggingBase):
        print(logger.log("Hello Ma!"))
