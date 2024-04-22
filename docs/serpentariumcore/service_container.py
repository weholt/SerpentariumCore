import inspect
import logging
from typing import Any, Callable, Self, Tuple, Type

logger = logging.getLogger("serpentariumcore")


class ServiceAlreadyRegistered(Exception):
    pass


class ServiceNotRegistered(Exception):
    pass


class InstanceIsNotSubclass(Exception):
    pass


class ConstructionFailed(Exception):
    pass


class MissingRequirements(Exception):
    def __init__(self, klass: str, missing_requirements: list[str], *args: Type) -> None:
        super().__init__(*args)
        self.klass = klass
        self.missing_requirements = missing_requirements

    def __str__(self) -> str:
        return f"Service {self.klass} requires the following services which are not avaible: {", ".join(self.missing_requirements)}"  # type: ignore # noqa: F401


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
    __current_namespace: str = __default_namespace
    __previous_namespace: str | None = None
    __namespace_resolver: Callable[[], str] | None = None

    def __new__(cls, namespace: str | None = None, lazy_construction: bool | None = None):  # type: ignore # noqa: F401
        if cls.__instance is None:
            cls.__instance = super(ServiceContainer, cls).__new__(cls)
        return cls.__instance

    def __init__(self, namespace: str | None = None, lazy_construction: bool | None = None) -> None:
        if namespace:
            ns = self.__check_namespace(namespace)
            self.set_namespace(ns)

        if self.__lazy_construction is None and lazy_construction is not None:
            self.__lazy_construction = lazy_construction

    def __check_namespace(self, namespace: str | None = None) -> str:
        if not namespace and self.__namespace_resolver:
            namespace = self.__namespace_resolver()
        ns = namespace or self.__current_namespace
        if ns not in self.__services:
            self.__services[ns] = {}
        return ns

    def construct[T](self, klass: T, namespace: str | None = None, **kwargs) -> T:
        if not inspect.isclass(klass):  # type: ignore # noqa: F401
            return klass

        ns = self.__check_namespace(namespace)
        klass_contstructor_args = inspect.getfullargspec(klass.__init__)
        reqs = {var_name: proto for var_name, proto in klass_contstructor_args.annotations.items()}

        params = {}
        params.update(kwargs)
        missing_requirements = []
        for k, v in reqs.items():
            if v in self.__services[ns]:
                inst = self.__services[ns][v]
                if inspect.isclass(inst):  # type: ignore # noqa: F401
                    inst = self.construct(inst, ns)
                params[k] = inst
            elif v:
                missing_requirements.append(v.__name__)

        if missing_requirements:
            raise MissingRequirements(klass.__name__, missing_requirements)

        # breakpoint()
        return klass(**params)

    def register(self, klass: Type, instance: Type, namespace: str | None = None) -> None:
        ns = self.__check_namespace(namespace)
        if not self.lazy_construction and inspect.isclass(instance):
            instance = self.construct(instance, ns)

        if klass in self.__services[ns]:
            raise ServiceAlreadyRegistered(f"Service {klass} is already registered.")
        self.__services[ns][klass] = instance

    def replace(self, klass: Type, instance: Type, namespace: str | None = None) -> None:
        ns = self.__check_namespace(namespace)
        self.__services[ns][klass] = instance

    def resolve[T](self, klass: Type[T], namespace: str | None = None) -> T | None:
        ns = self.__check_namespace(namespace)
        if klass in self.__services[ns]:  # pragma: no cover
            item = self.__services[ns][klass]
            args = ()
            kwargs = {}
            if isinstance(item, ServiceArgument):
                inner_klass, kwargs = item.unwrap()
                item = inner_klass
            if self.lazy_construction and inspect.isclass(item):
                item = self.construct(item, ns, **kwargs)

            return item
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
        if self.__previous_namespace:  # type: ignore # noqa: F401
            self.__current_namespace = self.__previous_namespace
        self.__previous_namespace = None

    def set_namespace_resolver(self, func: Callable[[], str]) -> None:
        self.__namespace_resolver = func

    def clear_namespace_resolver(self) -> None:
        self.__namespace_resolver = None

    @property
    def lazy_construction(self):
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


class ServiceRegistrator:
    def __init__(self, klass, namespace: str | None = None):
        self.klass = klass
        self.namespace = namespace
        self.args: Tuple = ()
        self.kwargs: dict[Any, Any] = {}
        self.service_arguments: ServiceArgument | None = None

    def with_arguments(self, service_arguments: Type[ServiceArgument]) -> Self:
        self.service_arguments = service_arguments
        return self

    def __call__[T](self, instance: T) -> T:
        if self.service_arguments is not None:
            self.service_arguments.for_service(instance)
            ServiceContainer().register(self.klass, self.service_arguments, namespace=self.namespace)
        else:
            ServiceContainer().register(self.klass, instance, namespace=self.namespace)
            logger.info(f"Service container registered {self.klass} -> {instance}")
        return instance
