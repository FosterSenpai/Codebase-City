# Identify circular import groups from FileConnection's
from src.file_connections import FileConnection


def _build_adjacency(connections: list[FileConnection]) -> dict[int, set[int]]:
    """Build a directed graph mapping file IDs to the files they import."""
    # Map each file ID to the set of file IDs it imports
    adjacency: dict[int, set[int]] = {}

    # Looping over connections
    for connection in connections:
        importer = connection.importer_file_id
        imported = connection.imported_file_id

        # Importers neighbour set on first appearance
        # Keep any dependencies recorder already
        if importer not in adjacency:
            adjacency[importer] = set()

        # Record directed connection : importer -> imported
        adjacency[importer].add(imported)

        # Include destination only files so traversal knows about them
        # empty set means file has no outgoing connections in this graph.
        if imported not in adjacency:
            adjacency[imported] = set()

    return adjacency


def _finishing_order(adjacency: dict[int, set[int]]) -> list[int]:
    """Return file IDs in deterministic depth first finishing order"""
    visited: set[int] = set()
    order: list[int] = []

    for start in sorted(adjacency):
        if start in visited:
            continue

        visited.add(start)
        stack = [(start, iter(sorted(adjacency[start])))]

        while stack:
            file_id, neighbours = stack[-1]

            # Take neighbour of current file
            neighbour = next(neighbours, None)

            if neighbour is None:
                # No neighbours left, file finished
                stack.pop()
                order.append(file_id)
            elif neighbour not in visited:
                # Pause this file and explore neighbour
                visited.add(neighbour)
                stack.append((neighbour, iter(sorted(adjacency[neighbour]))))

    return order


def _reverse_adjacency(adjacency: dict[int, set[int]]) -> dict[int, set[int]]:
    """Reverse every directed connection while preserving all file IDs."""
    reversed_adjacency: dict[int, set[int]] = {}

    for file_id in adjacency:
        reversed_adjacency[file_id] = set()

    for file_id, neighbours in adjacency.items():
        for neighbour in neighbours:
            reversed_adjacency[neighbour].add(file_id)

    return reversed_adjacency


def find_import_cycles(connections: list[FileConnection]) -> list[list[int]]:
    """Return sorted circular import groups as lists of file IDs"""
    adjacency = _build_adjacency(connections)
    order = _finishing_order(adjacency)
    reversed_adjacency = _reverse_adjacency(adjacency)

    visited: set[int] = set()
    cycles: list[list[int]] = []

    # Explore reversed graph
    for start in reversed(order):
        if start in visited:
            continue

        component: list[int] = []
        stack = [start]
        visited.add(start)

        # Traverse everything reachable that hasnt been visited
        while stack:
            file_id = stack.pop()
            component.append(file_id)

            for neighbour in sorted(reversed_adjacency[file_id], reverse=True):
                if neighbour not in visited:
                    visited.add(neighbour)
                    stack.append(neighbour)

        # Multi file cycles and single files that import themselves.
        if len(component) > 1 or start in adjacency[start]:
            cycles.append(sorted(component))

    return sorted(cycles)
