import importlib.util
import inspect
import logging
import os
import tempfile
import time
from inspect import getmembers, isfunction
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, Self, Tuple, Type

logger = logging.getLogger("serpentariumcore")


def implements_protocol(cls: Type, protocol: Type) -> bool:
    cls_attrs = [name for name, _ in getmembers(cls, predicate=isfunction)]
    protocol_attrs = [name for name, _ in getmembers(protocol, predicate=isfunction)]
    return all(attr in cls_attrs for attr in protocol_attrs if not attr.startswith("__"))


class ServiceAlreadyRegistered(Exception):
    pass


class ServiceNotRegistered(Exception):
    pass


class InstanceIsNotSubclass(Exception):
    pass


class ConstructionFailed(Exception):
    pass


class ServiceRequiresOtherServiceWithIdenticalProtocol(Exception):
    pass


class MissingRequirements(Exception):
    def __init__(self, klass: str, missing_requirements: list[str], *args: Type) -> None:
        super().__init__(*args)
        self.klass = klass
        self.missing_requirements = missing_requirements

    def __str__(self) -> str:
        return f"Service {self.klass} requires the following services which are not avaible: {", ".join(self.missing_requirements)}"  # noqa: F401 # pragma: no cover


class ServiceArgument:
    def __init__(self, **kwargs: dict[Any, Any]) -> None:
        self.klass = None
        self.kwargs = kwargs

    def for_service(self, klass: Any) -> Self:
        self.klass = klass
        return self

    def unwrap(self) -> Tuple[Any, dict[str, Any]]:
        return self.klass, self.kwargs


class ServiceContainer:
    __default_namespace: str = "default"
    __lazy_construction: bool | None = None
    __instance = None
    __services: dict[str, dict[Type, Type]] = {}
    __multi_services: dict[Type, list[Type]] = {}
    __current_namespace: str = __default_namespace
    __previous_namespace: str | None = None
    __namespace_resolver: Callable[[], str] | None = None
    __raise_exception_on_double_registrations: bool = False

    def __new__(cls, namespace: str | None = None, lazy_construction: bool | None = None):  # type: ignore # noqa: F401 # pragma: no cover
        if cls.__instance is None:
            cls.__instance = super(ServiceContainer, cls).__new__(cls)
        return cls.__instance

    def __init__(self, namespace: str | None = None, lazy_construction: bool | None = None) -> None:
        if namespace:
            ns = self.__check_namespace(namespace)
            self.set_namespace(ns)

        if self.__lazy_construction is None and lazy_construction is not None:
            self.__lazy_construction = lazy_construction

    def setconfig(self, values: dict[str, Any]) -> None:
        for attr, value in values.items():
            if attr in ["instance", "services", "multi_services"]:
                continue
            if hasattr(self, f"_ServiceContainer__{attr}"):  # noqa: F401 # pragma: no cover
                setattr(self, f"_ServiceContainer__{attr}", value)

    def __check_namespace(self, namespace: str | None = None) -> str:
        if not namespace and self.__namespace_resolver:
            namespace = self.__namespace_resolver()
        ns = namespace or self.__current_namespace
        if ns not in self.__services:
            self.__services[ns] = {}
        return ns

    def construct(self, klass: Type, namespace: str | None = None, **kwargs: dict[Any, Any]) -> Type[Any]:
        if not inspect.isclass(klass):  # noqa: F401 # pragma: no cover
            return klass

        ns = self.__check_namespace(namespace)
        klass_contstructor_args = inspect.getfullargspec(klass.__init__)
        reqs = {var_name: proto for var_name, proto in klass_contstructor_args.annotations.items()}

        params: dict[Any, Any] = {}
        params.update(kwargs)
        missing_requirements = []
        for k, v in reqs.items():
            if v in self.__services[ns]:
                inst = self.__services[ns][v]
                if inspect.isclass(inst):  # noqa: F401 # pragma: no cover
                    inst = self.construct(inst, ns)
                params[k] = inst
            elif v:
                missing_requirements.append(v.__name__)

        if missing_requirements:
            raise MissingRequirements(klass.__name__, missing_requirements)

        return klass(**params)  # type: ignore

    def register(self, klass: Type, instance: Type, namespace: str | None = None) -> None:
        ns = self.__check_namespace(namespace)
        if not self.lazy_construction and inspect.isclass(instance):
            instance = self.construct(instance, ns)

        if self.__raise_exception_on_double_registrations and klass in self.__services[ns]:
            raise ServiceAlreadyRegistered(f"Service {klass} is already registered.")
        self.__services[ns][klass] = instance

    def multi_register(self, klass: Type, instance: Type) -> None:
        assert implements_protocol(instance, klass)
        self.__multi_services.setdefault(klass, []).append(instance)

        klass_contstructor_args = inspect.getfullargspec(instance.__init__)
        reqs = [proto for _, proto in klass_contstructor_args.annotations.items()]
        if klass in reqs:
            raise ServiceRequiresOtherServiceWithIdenticalProtocol(instance)

    def resolve_multi(self, klass: Type) -> Iterable[Type]:
        for service in self.__multi_services.get(klass, []):
            yield self.construct(service)

    def replace(self, klass: Type, instance: Type, namespace: str | None = None) -> None:
        ns = self.__check_namespace(namespace)
        self.__services[ns][klass] = instance

    def resolve(self, klass: Type, namespace: str | None = None) -> Type | None:
        ns = self.__check_namespace(namespace)
        if klass in self.__services[ns]:
            item = self.__services[ns][klass]
            kwargs: dict[Any, Any] = {}
            if isinstance(item, ServiceArgument):
                inner_klass, kwargs = item.unwrap()  # type: ignore
                item = inner_klass
            if self.lazy_construction and inspect.isclass(item):
                item = self.construct(item, ns, **kwargs)

            return item  # noqa: F401 # pragma: no cover
        return None

    def remove(self, klass: Type, namespace: str | None = None) -> None:
        ns = self.__check_namespace(namespace)
        if not inspect.isclass(klass):
            klass = klass.__class__
        if klass in self.__services[ns]:  # pragma: no cover
            del self.__services[ns][klass]

    def clear(self) -> None:
        self.__services.clear()
        self.__current_namespace = self.__default_namespace
        self.__previous_namespace = None
        self.__lazy_construction = None

    def set_namespace(self, namespace: str) -> None:
        self.__previous_namespace = self.__current_namespace
        self.__current_namespace = namespace

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        if self.__previous_namespace:  # noqa: F401 # pragma: no cover
            self.__current_namespace = self.__previous_namespace
        self.__previous_namespace = None

    def set_namespace_resolver(self, func: Callable[[], str]) -> None:
        self.__namespace_resolver = func

    def clear_namespace_resolver(self) -> None:
        self.__namespace_resolver = None

    @property
    def lazy_construction(self) -> bool:
        return self.__lazy_construction in [True, None]

    @property
    def namespace(self) -> str:
        if self.__namespace_resolver:
            return self.__namespace_resolver()
        return self.__current_namespace

    def sanity_check(self) -> bool:
        for ns in self.__services:
            for proto in self.__services[ns]:
                self.resolve(proto, ns)
        return True


class ServiceRegistration:
    def __init__(self, klass: Type, namespace: str | None = None):
        self.klass = klass
        self.namespace = namespace
        self.args: Tuple = ()
        self.kwargs: dict[Any, Any] = {}
        self.service_arguments: ServiceArgument | None = None

    def with_arguments(self, service_arguments: Type[ServiceArgument]) -> Self:
        self.service_arguments = service_arguments  # type: ignore
        return self

    def __call__(self, instance: Type) -> Type:
        if self.service_arguments is not None:
            self.service_arguments.for_service(instance)
            ServiceContainer().register(self.klass, self.service_arguments, namespace=self.namespace)  # type: ignore
        else:
            ServiceContainer().register(self.klass, instance, namespace=self.namespace)
            logger.info(f"Service container registered {self.klass} -> {instance}")
        return instance


def resolve(klass: Type, namespace: str | None = None) -> Type | None:
    "Shortcut for ServiceContainer().resolve(...)"
    return ServiceContainer().resolve(klass, namespace)


def register_as(klass: Type, namespace: str | None = None) -> Callable[[Type], Type]:
    "Shortcut for ServiceRegistration(...)"

    def decorator(cls: Type) -> Type:
        ServiceContainer().register(klass, cls, namespace=namespace)
        return cls

    return decorator


def multi_register_as(klass: Type) -> Callable[[Type], Type]:
    def decorator(cls: Type) -> Type:
        ServiceContainer().multi_register(klass, cls)
        return cls

    return decorator


def resolve_multi(klass: Type) -> Iterable[Type]:
    return ServiceContainer().resolve_multi(klass)


def import_module_from_file(file_path: Path) -> Any:
    # Get the module name from the file name
    module_name = file_path.stem

    # Load the module from the file
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    return module


class ServiceDiscovery:
    __instance = None
    __verbose: bool = True
    __PID_FILE = "sd5435435345.pid"

    def __new__(cls, verbose: bool = True) -> Self:  # type: ignore # noqa: F401 # pragma: no cover
        if cls.__instance is None:
            cls.__instance = super(ServiceDiscovery, cls).__new__(cls)
        return cls.__instance

    def __init__(self, verbose: bool = True) -> None:
        self.__verbose = verbose

    def log(self, msg: str) -> None:
        if self.__verbose:
            print(msg)
        else:
            logger.info(msg)

    def discover(self, module: Any, verbose: bool = True) -> None:
        temp_dir = tempfile.gettempdir()
        pid = os.path.join(temp_dir, self.__PID_FILE)
        if os.path.exists(pid):
            return

        with open(pid, "w") as f:
            f.write("0")

        start = time.time()
        self.log("Starting service discovery ...")
        for unit in Path(module.__file__).parent.glob("**/*.py"):
            if unit.name.startswith("test_") or unit.name.startswith("__"):
                continue
            try:
                import_module_from_file(unit)
            except Exception as ex:
                pass
        os.remove(pid)
        self.log(f"Finished discovery in {time.time()-start} seconds.")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        pass
