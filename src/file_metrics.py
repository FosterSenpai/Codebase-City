from dataclasses import dataclass


@dataclass
class FileMetrics:
    """Store measurements for a source file"""

    file_id: int
    line_count: int
