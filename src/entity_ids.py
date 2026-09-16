class EntityIdAllocator:
    """Issues and manages sequential IDs to entity objects within the repository"""

    def __init__(self) -> None:
        self.next_available_id = 1

    def allocate(self) -> int:
        current_id = self.next_available_id
        self.next_available_id += 1
        return current_id
