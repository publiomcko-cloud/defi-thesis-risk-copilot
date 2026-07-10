from abc import ABC, abstractmethod
from typing import Any


class DataSourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def unknown_fields(required_fields: list[str], data: dict[str, Any]) -> list[str]:
    return [
        field
        for field in required_fields
        if data.get(field) is None or data.get(field) == ""
    ]
