import unittest

from src.entity_ids import EntityIdAllocator


class TestEntityIds(unittest.TestCase):
    def test_incrementing_ids_starting_at_one(self):
        allocator = EntityIdAllocator()
        allocated_ids = [allocator.allocate() for _ in range(3)]

        self.assertEqual(allocated_ids, [1, 2, 3])

    def test_allocators_have_independent_counters(self):
        first_allocator = EntityIdAllocator()
        second_allocator = EntityIdAllocator()

        first_allocator.allocate()
        first_allocator.allocate()

        self.assertEqual(second_allocator.allocate(), 1)

        self.assertEqual(first_allocator.allocate(), 3)
        self.assertEqual(second_allocator.allocate(), 2)
