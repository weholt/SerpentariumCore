import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger("redtoolbox:service-container")

T = TypeVar("T")


class ServiceAlreadyRegistered(Exception):
    pass


class ServiceNotRegistered(Exception):
    pass


class InstanceIsNotSubclass(Exception):
    pass


class WrapperService:

    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        self.args = args
        self.kwargs = kwargs

    def unwrap(self):
        return self.instance, self.args, self.kwargs


class ServiceContainer:

    __default_namespace: str = "default"
    __instance = None
    __services: dict = {}
    __current_namespace: str = __default_namespace
    __previous_namespace: str | None = None
    __namespace_resolver: Callable[[], str] | None = None

    def __new__(cls, namespace: str | None = None):  # type: ignore noqa
        if cls.__instance is None:
            cls.__instance = super(ServiceContainer, cls).__new__(cls)
        return cls.__instance

    def __init__(self, namespace: str | None = None):
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

    def register(self, klass, instance, namespace: str | None = None):
        ns = self.__check_namespace(namespace)
        if klass in self.__services[ns]:
            raise ServiceAlreadyRegistered(f"Service {klass} is already registered.")
        self.__services[ns][klass] = instance

    def replace(self, klass, instance, namespace: str | None = None):
        ns = self.__check_namespace(namespace)
        self.__services[ns][klass] = instance

    def resolve(self, klass: T, namespace: str | None = None) -> T | None:
        ns = self.__check_namespace(namespace)
        if klass in self.__services[ns]:
            item = self.__services[ns][klass]
            if isinstance(item, WrapperService):
                instance, args, kwargs = item.unwrap()
                item = instance(*args, **kwargs)
            return item

    def remove(self, klass, namespace: str | None = None):
        ns = self.__check_namespace(namespace)
        if isinstance(klass, object):
            klass = klass.__class__
        if klass in self.__services[ns]:
            del self.__services[ns][klass]

    def clear(self):
        self.__services.clear()
        self.__current_namespace = self.__default_namespace
        self.__previous_namespace = None

    def set_namespace(self, namespace: str) -> None:
        self.__previous_namespace = self.__current_namespace
        self.__current_namespace = namespace

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore noqa
        if self.__previous_namespace:
            self.__current_namespace = self.__previous_namespace
        self.__previous_namespace = None

    def set_namespace_resolver(self, func: Callable[[], str]) -> None:
        self.__namespace_resolver = func

    def clear_namespace_resolver(self) -> None:
        self.__namespace_resolver = None

    @property
    def namespace(self):
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

    def wrap(self, wrapper_class):
        self.wrapper_class = wrapper_class
        return self

    def __call__(self, instance) -> Any:
        if self.wrapper_class:
            ServiceContainer().register(self.klass, self.wrapper_class(instance, self.args, self.kwargs), namespace=self.namespace)
        else:
            ServiceContainer().register(self.klass, instance(*self.args, **self.kwargs), namespace=self.namespace)
            logger.info(f"Service container registered {self.klass} -> {instance}")
        return instance
