from typing import Protocol

from serpentariumcore import multi_register_as


class TheProtocol(Protocol):
    def speak(self, msg: str) -> str:
        return msg


@multi_register_as(TheProtocol)
class Teacher:
    def speak(self, msg: str) -> str:
        return f"Screams '{msg}"
