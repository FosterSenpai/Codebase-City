import unittest

from src.file_connections import FileConnection
from src.import_cycles import (
    _build_adjacency,
    _finishing_order,
    _reverse_adjacency,
    find_import_cycles,
)


class ImportCycleTests(unittest.TestCase):
    def test_builds_adjacency_with_multiple_dependencies(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(1, 3, []),
            FileConnection(2, 3, []),
        ]

        # Preserve all outgoing dependencies and include destination-only files.
        self.assertEqual(
            _build_adjacency(connections),
            {1: {2, 3}, 2: {3}, 3: set()},
        )

    def test_preserves_reverse_and_self_connections(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(2, 1, []),
            FileConnection(2, 2, []),
        ]

        # Retain both directions and self-imports for later cycle detection.
        self.assertEqual(
            _build_adjacency(connections),
            {1: {2}, 2: {1, 2}},
        )

    def test_duplicate_connections_do_not_duplicate_neighbours(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(1, 2, []),
        ]

        # A dependency should appear only once in each neighbour set.
        self.assertEqual(
            _build_adjacency(connections),
            {1: {2}, 2: set()},
        )

    def test_empty_connections_produce_empty_adjacency(self):
        # No connections should produce an empty graph.
        self.assertEqual(_build_adjacency([]), {})

    def test_finishing_order_processes_dependencies_before_importers(self):
        adjacency = {1: {2}, 2: {3}, 3: set()}

        # A dependency chain should finish from its deepest file back to its start.
        self.assertEqual(_finishing_order(adjacency), [3, 2, 1])

    def test_finishing_order_handles_cycles_and_disconnected_files(self):
        adjacency = {1: {2}, 2: {1}, 3: {3}, 4: set()}

        # Visit every file once, including cycles, self-imports, and isolated files.
        self.assertEqual(_finishing_order(adjacency), [2, 1, 3, 4])

    def test_finishing_order_is_deterministic_for_branching_graph(self):
        first = {1: {2, 3}, 2: {4}, 3: {4}, 4: set()}
        reordered = {4: set(), 3: {4}, 2: {4}, 1: {3, 2}}

        # Sorted traversal should give the same result regardless of dictionary order.
        self.assertEqual(_finishing_order(first), [4, 2, 3, 1])
        self.assertEqual(_finishing_order(reordered), [4, 2, 3, 1])

    def test_finishing_order_handles_long_chains_without_recursion(self):
        adjacency = {file_id: {file_id + 1} for file_id in range(2000)}
        adjacency[2000] = set()

        # An explicit stack should handle deep graphs without recursive calls.
        self.assertEqual(
            _finishing_order(adjacency),
            list(range(2000, -1, -1)),
        )

    def test_empty_graph_has_empty_finishing_order(self):
        # No files means no finishing order.
        self.assertEqual(_finishing_order({}), [])

    def test_reverses_connections_and_preserves_isolated_files(self):
        adjacency = {
            1: {2, 3},
            2: {3},
            3: set(),
            4: set(),
        }

        result = _reverse_adjacency(adjacency)

        # Reverse each edge while retaining destination-only and isolated files.
        self.assertEqual(
            result,
            {1: set(), 2: {1}, 3: {1, 2}, 4: set()},
        )

        # Reversing the graph should not change the original connections.
        self.assertEqual(
            adjacency,
            {1: {2, 3}, 2: {3}, 3: set(), 4: set()},
        )

    def test_reversal_preserves_self_and_bidirectional_connections(self):
        adjacency = {1: {2}, 2: {1, 2}}

        # Mutual imports and self-imports still exist after reversal.
        self.assertEqual(
            _reverse_adjacency(adjacency),
            {1: {2}, 2: {1, 2}},
        )

    def test_reversing_twice_restores_original_graph(self):
        adjacency = {1: {2}, 2: {3}, 3: set()}

        # Reversing every edge twice should recover the starting graph.
        self.assertEqual(
            _reverse_adjacency(_reverse_adjacency(adjacency)),
            adjacency,
        )

    def test_reversing_empty_graph_returns_empty_graph(self):
        # Empty input should produce an empty result.
        self.assertEqual(_reverse_adjacency({}), {})

    def test_finds_multi_file_cycle(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(2, 3, []),
            FileConnection(3, 1, []),
        ]

        # All three mutually reachable files should form one circular group.
        self.assertEqual(find_import_cycles(connections), [[1, 2, 3]])

    def test_acyclic_connections_produce_no_cycles(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(1, 3, []),
            FileConnection(2, 4, []),
            FileConnection(3, 4, []),
        ]

        # Shared dependencies alone do not create a circular import.
        self.assertEqual(find_import_cycles(connections), [])

    def test_keeps_cycles_separate_across_one_way_connection(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(2, 1, []),
            FileConnection(2, 3, []),
            FileConnection(3, 4, []),
            FileConnection(4, 3, []),
        ]

        # A one-way bridge must not merge two separate circular groups.
        self.assertEqual(find_import_cycles(connections), [[1, 2], [3, 4]])

    def test_finds_self_import_without_including_non_circular_files(self):
        connections = [
            FileConnection(1, 1, []),
            FileConnection(2, 3, []),
        ]

        # A self-import is circular, but the disconnected chain is not.
        self.assertEqual(find_import_cycles(connections), [[1]])

    def test_excludes_files_leading_into_or_out_of_cycle(self):
        connections = [
            FileConnection(1, 2, []),
            FileConnection(2, 3, []),
            FileConnection(3, 2, []),
            FileConnection(3, 4, []),
        ]

        # Only mutually reachable files belong to the circular group.
        self.assertEqual(find_import_cycles(connections), [[2, 3]])

    def test_cycle_groups_are_independent_of_connection_order(self):
        connections = [
            FileConnection(4, 3, []),
            FileConnection(2, 1, []),
            FileConnection(3, 4, []),
            FileConnection(1, 2, []),
        ]

        # Group members and groups should remain sorted for either input order.
        self.assertEqual(find_import_cycles(connections), [[1, 2], [3, 4]])
        self.assertEqual(
            find_import_cycles(list(reversed(connections))),
            [[1, 2], [3, 4]],
        )

    def test_empty_connections_produce_no_cycles(self):
        # Empty input should return an empty list rather than None.
        self.assertEqual(find_import_cycles([]), [])
