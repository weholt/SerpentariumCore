import logging
import inspect
from typing import Any, Callable, Type, Tuple, Self

logger = logging.getLogger("serpentariumcore")


class ServiceAlreadyRegistered(Exception):
    pass


class ServiceNotRegistered(Exception):
    pass


class InstanceIsNotSubclass(Exception):
    pass


class MissingRequirements(Exception):

    def __init__(self, klass: str, missing_requirements: list[str], *args: Type) -> None:
        super().__init__(*args)
        self.klass = klass
        self.missing_requirements = missing_requirements

    def __str__(self) -> str:
        return f"Service {self.klass} requires the following services which are not avaible: {", ".join(self.missing_requirements)}"


class WrapperService:

    def __init__(self, instance: Type, *args: Any, **kwargs: dict[Any, Any]) -> None:
        self.instance = instance
        self.args = args
        self.kwargs = kwargs

    def unwrap(self) -> Tuple[Any, Any, dict[str, Any]]:
        return self.instance, self.args, self.kwargs


class ServiceContainer:

    __default_namespace: str = "default"
    __instance = None
    __services: dict[str, dict[Type, Type]] = {}
    __current_namespace: str = __default_namespace
    __previous_namespace: str | None = None
    __namespace_resolver: Callable[[], str] | None = None

    def __new__(cls, namespace: str | None = None):  # type: ignore
        if cls.__instance is None:
            cls.__instance = super(ServiceContainer, cls).__new__(cls)
        return cls.__instance

    def __init__(self, namespace: str | None = None) -> None:
        if namespace:
            ns = self.__check_namespace(namespace)
            self.set_namespace(ns)

    def __check_namespace(self, namespace: str | None = None) -> str:
        if not namespace and self.__namespace_resolver:
            namespace = self.__namespace_resolver()
        ns = namespace or self.__current_namespace
        if ns not in self.__services:
            self.__services[ns] = {}
        return ns

    def construct[T](self, klass: T, namespace: str | None = None) -> T:
        ns = self.__check_namespace(namespace)
        klass_contstructor_args = inspect.getfullargspec(klass.__init__)
        reqs = {var_name: proto for var_name, proto in klass_contstructor_args.annotations.items()}

        params = {}
        missing_requirements = []
        for k, v in reqs.items():
            if v in self.__services[ns]:
                params[k] = self.__services[ns][v]
            else:
                missing_requirements.append(v.__name__)

        if missing_requirements:
            raise MissingRequirements(klass.__name__, missing_requirements)
        return klass(**params)

    def register(self, klass: Type, instance: Type, namespace: str | None = None) -> None:
        ns = self.__check_namespace(namespace)
        if inspect.isclass(instance):
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
            if isinstance(item, WrapperService):
                instance, args, kwargs = item.unwrap()
                item = instance(*args, **kwargs)
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

    def set_namespace(self, namespace: str) -> None:
        self.__previous_namespace = self.__current_namespace
        self.__current_namespace = namespace

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        if self.__previous_namespace:
            self.__current_namespace = self.__previous_namespace
        self.__previous_namespace = None

    def set_namespace_resolver(self, func: Callable[[], str]) -> None:
        self.__namespace_resolver = func

    def clear_namespace_resolver(self) -> None:
        self.__namespace_resolver = None

    @property
    def namespace(self) -> str:
        if self.__namespace_resolver:
            return self.__namespace_resolver()
        return self.__current_namespace


class ServiceRegistrator:

    def __init__(self, klass, namespace: str | None = None, *args, **kwargs):
        self.klass = klass
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.namespace = namespace
        self.wrapper_class = None

    def wrap(self, wrapper_class: WrapperService) -> Self:
        self.wrapper_class = wrapper_class
        return self

    def __call__[T](self, instance: T) -> T:
        if self.wrapper_class is not None:
            ServiceContainer().register(self.klass, self.wrapper_class(instance, self.args, self.kwargs), namespace=self.namespace)
        else:
            ServiceContainer().register(self.klass, instance(*self.args, **self.kwargs), namespace=self.namespace)
            logger.info(f"Service container registered {self.klass} -> {instance}")
        return instance
