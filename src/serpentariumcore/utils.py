# # from typing import Any, List, Protocol
# # import sys
# # import inspect


# # def print_classes(parent_class: Any) -> dict[Any, Any]:
# #     result = {}
# #     for _, obj in inspect.getmembers(sys.modules[__name__]):
# #         if inspect.isclass(obj) and issubclass(obj, parent_class):
# #             if hasattr(obj, "target"):
# #                 if target := obj.target():
# #                     result[target] = obj

# #     import pprint

# #     pprint.pprint(result)
# #     return result


# import sys, inspect, os
# from typing import Type
# from importlib import import_module

# def current_module_name() -> str | None:
#     try:
#         current_file: str = sys.modules[__name__].__file__
#     except KeyError as ex:
#         print(f"Error getting current module: {ex}")
#         return
#     return os.path.dirname(current_file).rsplit(os.sep)[-1]


# def get_classes_from_module(module) -> list[Type]:
#     return [f for f in inspect.getmembers(import_module(module)) if inspect.isclass(f)]
