# from typing import Any, List, Protocol
# import sys
# import inspect


# def print_classes(parent_class: Any) -> dict[Any, Any]:
#     result = {}
#     for _, obj in inspect.getmembers(sys.modules[__name__]):
#         if inspect.isclass(obj) and issubclass(obj, parent_class):
#             if hasattr(obj, "target"):
#                 if target := obj.target():
#                     result[target] = obj

#     import pprint

#     pprint.pprint(result)
#     return result
