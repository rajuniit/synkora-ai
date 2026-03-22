"""Consistent hashing implementation for bot-to-worker assignment.

Consistent hashing ensures that:
1. The same bot always goes to the same worker (deterministic)
2. When workers join/leave, only ~1/N bots need to be reassigned
3. No central coordinator needed for assignment decisions
"""

import hashlib
from bisect import bisect_left


class ConsistentHash:
    """Consistent hash ring for distributing bots across workers.

    Uses virtual nodes (replicas) to improve distribution uniformity.
    Each physical worker is represented by multiple points on the ring.
    """

    def __init__(self, nodes: list[str] | None = None, replicas: int = 100):
        """Initialize the consistent hash ring.

        Args:
            nodes: Initial list of worker IDs to add to the ring
            replicas: Number of virtual nodes per physical worker
        """
        self.replicas = replicas
        self.ring: list[int] = []
        self.node_map: dict[int, str] = {}
        self._nodes: set[str] = set()

        if nodes:
            for node in nodes:
                self.add_node(node)

    def add_node(self, node: str) -> None:
        """Add a worker to the hash ring.

        Args:
            node: Worker ID to add
        """
        if node in self._nodes:
            return  # Already in ring

        self._nodes.add(node)
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            self.ring.append(key)
            self.node_map[key] = node
        self.ring.sort()

    def remove_node(self, node: str) -> None:
        """Remove a worker from the hash ring.

        Args:
            node: Worker ID to remove
        """
        if node not in self._nodes:
            return  # Not in ring

        self._nodes.discard(node)
        for i in range(self.replicas):
            key = self._hash(f"{node}:{i}")
            if key in self.node_map:
                self.ring.remove(key)
                del self.node_map[key]

    def get_node(self, key: str) -> str:
        """Get the worker assigned to handle a given key (bot ID).

        Args:
            key: The key to look up (typically a bot ID)

        Returns:
            Worker ID assigned to this key

        Raises:
            ValueError: If no nodes are available in the ring
        """
        if not self.ring:
            raise ValueError("No workers available in the hash ring")

        h = self._hash(key)
        idx = bisect_left(self.ring, h)

        # Wrap around if we're past the end of the ring
        if idx >= len(self.ring):
            idx = 0

        return self.node_map[self.ring[idx]]

    def get_all_nodes(self) -> list[str]:
        """Get all worker IDs in the ring.

        Returns:
            List of worker IDs
        """
        return list(self._nodes)

    def get_node_count(self) -> int:
        """Get the number of workers in the ring.

        Returns:
            Number of workers
        """
        return len(self._nodes)

    def get_keys_for_node(self, node: str, all_keys: list[str]) -> list[str]:
        """Get all keys that would be assigned to a specific node.

        Useful for determining which bots a worker should manage.

        Args:
            node: Worker ID to check
            all_keys: List of all keys (bot IDs) to check

        Returns:
            List of keys assigned to the specified node
        """
        if not self.ring:
            return []

        return [key for key in all_keys if self.get_node(key) == node]

    def _hash(self, key: str) -> int:
        """Generate a hash value for a key.

        Uses MD5 for good distribution (not for security).

        Args:
            key: String to hash

        Returns:
            Integer hash value
        """
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def __contains__(self, node: str) -> bool:
        """Check if a node is in the ring."""
        return node in self._nodes

    def __len__(self) -> int:
        """Return number of nodes in the ring."""
        return len(self._nodes)
