# Serpentarium Core

Serpentarium Core is a basic service container for python using the typing Protocol
to define interfaces and type hints to resolve construction requirements for services.

Thanks ChatGPT for that name ;-)

## What is it?

> ### What is the Service Container pattern?
> The Service Container pattern is a design pattern that provides a centralized location for managing application services. A service is a class or module that provides a specific functionality, such as authentication, database access, or email sending. By separating services from components, we can achieve greater separation of concerns and better maintainability of our codebase.

> The Service Container pattern works by registering services with a central container, which can then be accessed by components as needed. This allows us to easily swap out services, add new services, or modify existing services without needing to modify individual components.

> [Source](https://dev.to/abdelrahmanallam/simplifying-dependency-injection-with-the-service-container-pattern-in-reactjs-and-ruby-on-rails-525m)

## Status:

* Version: 0.4.1
* Status: In development / Alpha / Proof-of-consept

## License:

* [GPL-3 - GNU GENERAL PUBLIC LICENSE Version 3.](https://www.gnu.org/licenses/gpl-3.0.txt)
* A low-cost commercial license will be available later.

**Why dual licensing you might ask?** Because the [current open-source licensing does not work](https://www.youtube.com/watch?v=9YQgNDLFYq8). It
only benefits the big commercial companies and leave the independant, personal developer with nothing.

This project will be available for commercial-non-GPL-use for a small fee, even smaller for
independant developers like me (like $10) and not much more for companies (perhaps $100).

## Tested with:

* Python version 3.12.2

## Planned features and todo`s

* Threads and async support? No clue on how thread-safe this is right now. Any help appreciated.

## Help

* [Read the documentation here](https://weholt.github.io/SerpentariumCore/)

## Installation

Clone main repository:

```bash

    $ git clone https://github.com/weholt/serpentariumcore.git
    $ cd serpentariumcore
    $ pip install .

```
Or

```bash

    $ pip install git+https://github.com/weholt/serpentariumcore.git
```

## Basic Usage

The following are actual test code, showing how to define a protocol and register an implemention
of that protocol in the service container, and then later on, resolve the Protocol by name
and get the implemention in return. We can also register services that depend on the implementation of other registered services,
and the actual construction of instances of those services will be handled by the service container:


```python

from serpentariumcore import register_as, resolve


class IB(Protocol):

    def howl(self) -> str: ...


@register_as(IB)
class B:

    def howl(self) -> str:
        return "YAHOOO!"


class IA(Protocol):

    def speak(self) -> str: ...


@register_as(IA)
class A:

    def __init__(self, b: IB):
        self.b = b

    def speak(self) -> str:
        return f"A says Hello and B says {self.b.howl()}"


if speaker := resolve(IA):
    assert "YAHOO" in speaker.speak()

```

Or without using the register_as and resolve shortcuts:

```python

from serpentariumcore import ServiceContainer


class TheTalkingProtocol(Protocol):
    def speak(self, sentence) -> str: ...


class Teacher:
    def speak(self, sentence) -> str:
        return f"The teacher screams '{sentence}'."


ServiceContainer().register(TheTalkingProtocol, Teacher())

if person := ServiceContainer().resolve(TheTalkingProtocol):
    assert person.speak(sentence="The dog sits on a mat") ==
        "The teacher screams 'The dog sits on a mat'."
```

### Namespaces

The service container also supports registering different implementations of the same protocol using namespaces:

```python


class IoOperations(Protocol):
    def read_file(self, filename: str) -> str: ...


class ActualIoOperations:
    def read_file(self, filename: str) -> str:
        return open(filename).read()

class TestingIoOperations:
    def read_file(self, filename: str) -> str:
        return "This is just some testing data"

ServiceContainer().register(IoOperations, ActualIoOperations)
ServiceContainer().register(IoOperations, TestingIoOperations, namespace="test")

if io := ServiceContainer().resolve(IoOperations):
    assert io.read_file("some_file.txt") ==
        "Data from the actual file on disk called some_file.txt"

if io := ServiceContainer().resolve(IoOperations, namespace="test"):
    assert io.read_file("some_file.txt") ==
        "This is just some testing data"

```

You can also use a function to calculate the correct namespace to use, for instance checking some setting, like this:

```python

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

ServiceContainer().register(
    FancyLoggingBase, LoggingTakingFunc(func=log_critical))

ServiceContainer().register(
    FancyLoggingBase, LoggingTakingFunc(func=log_debug), namespace="debug")

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

```

In the example above you can see that we do no change to the actual code using the service,
but what implementation is used is calculated based on the settings.


## Contributing & Reporting Issues

- Want to contribute directly to the source? Send me a line on thomas@weholt.org
- Any contribution is higly welcome, be it constructive critisism, ideas, testing and reporting bugs or anything else :-)
- [Issues are reported here ](https://github.com/weholt/SerpentariumCore/issues)

## Release notes

### Version 0.4.1

- Multi-registration of services & setconfig for run-time changes to your service container.

### Version 0.3.0

- Small refactoring and added two shortcuts for registration and resolving of services; register_as & resolve.

### Version 0.2.1

- Added github pages for documentation. More docs coming soon :-)

### Version 0.2.0

- Fixed a few bugs discovered while adding more unittest.
- Added support for lazy construction of instances.
- Added a ServiceArgument class for supplying your service with run-time arguments

### Version 0.1.0

- First initial release.
