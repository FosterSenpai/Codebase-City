"""
Contains data structures that represent folders, files, classes, functions and methods.
Should be built by the different language analyzers and used in constructing the city.
"""

from dataclasses import dataclass
from enum import Enum


class EntityType(Enum):
    FOLDER = "folder"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


@dataclass
class SourceLocation:
    path: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass
class CodeEntity:
    id: int
    name: str
    entity_type: EntityType

    location: SourceLocation
    parent_id: int | None = None  # ID of entity containing this entity
