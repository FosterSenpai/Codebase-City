from dataclasses import dataclass
from enum import Enum


class HeightMetric(Enum):
    """Available measurements for calculating building height, adding more"""

    LINES = "lines"
    CONNECTIONS = "connections"


@dataclass
class Building:
    """
    x and z locate the centre of the buildings footprint; its base sits at y = 0
    """

    file_id: int
    x: float
    z: float
    width: float
    depth: float
    height: float
