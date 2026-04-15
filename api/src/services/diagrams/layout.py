"""
Auto-layout engine for diagram nodes without explicit positions.

Uses a layered (Sugiyama-style) approach:
1. Topological sort (Kahn's algorithm)
2. Layer assignment (longest-path method)
3. Within-layer ordering (barycenter heuristic)
4. Coordinate assignment with centering

Handles cycles gracefully by breaking back-edges, supports container-aware
grouping for nodes sharing a ``group`` property, and auto-sizes the overall
diagram to fit all content.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_NODE_WIDTH = 200
_NODE_HEIGHT = 80
_LABEL_CHAR_WIDTH = 8  # approximate px per character for sizing long labels
_MIN_NODE_WIDTH = 180
_MAX_NODE_WIDTH = 340

_H_SPACING = 260  # horizontal spacing between nodes in the same layer
_V_SPACING = 160  # vertical spacing between layers

_PADDING = 80  # padding around the overall diagram
_GROUP_PADDING = 40  # padding inside container boxes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node_width_for_label(label: str) -> int:
    """Return an appropriate node width based on label length."""
    estimated = len(label) * _LABEL_CHAR_WIDTH + 32  # 16px padding each side
    return max(_MIN_NODE_WIDTH, min(estimated, _MAX_NODE_WIDTH))


def _edge_endpoints(arrow: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract (source, target) from an arrow dict, supporting both key formats."""
    src = arrow.get("source") or arrow.get("from")
    tgt = arrow.get("target") or arrow.get("to")
    return src, tgt


# ---------------------------------------------------------------------------
# Graph analysis
# ---------------------------------------------------------------------------


def _build_graph(
    node_ids: set[str],
    arrows: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Build adjacency list and in-degree map from arrows.

    Only edges whose both endpoints are in *node_ids* are considered.
    Returns (adjacency, in_degree).
    """
    adj: dict[str, list[str]] = defaultdict(list)
    in_deg: dict[str, int] = dict.fromkeys(node_ids, 0)

    for arrow in arrows:
        src, tgt = _edge_endpoints(arrow)
        if src and tgt and src in node_ids and tgt in node_ids:
            adj[src].append(tgt)
            in_deg.setdefault(tgt, 0)
            in_deg[tgt] += 1
            in_deg.setdefault(src, 0)

    return adj, in_deg


def _topological_sort_kahn(
    node_ids: set[str],
    adj: dict[str, list[str]],
    in_deg: dict[str, int],
) -> list[str]:
    """Kahn's algorithm. Handles cycles by breaking back-edges.

    Returns a valid ordering of all *node_ids* even when cycles exist.
    """
    in_deg = dict(in_deg)  # shallow copy so we can mutate
    queue: deque[str] = deque()
    for nid in node_ids:
        if in_deg.get(nid, 0) == 0:
            queue.append(nid)

    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in adj.get(node, []):
            in_deg[neighbour] -= 1
            if in_deg[neighbour] == 0:
                queue.append(neighbour)

    # If there are remaining nodes they are part of cycles -- append them in
    # deterministic order so the layout is stable across calls.
    remaining = sorted(node_ids - set(order))
    if remaining:
        order.extend(remaining)

    return order


# ---------------------------------------------------------------------------
# Layer assignment (longest-path)
# ---------------------------------------------------------------------------


def _assign_layers(
    topo_order: list[str],
    adj: dict[str, list[str]],
    node_ids: set[str],
) -> dict[str, int]:
    """Assign each node to a layer using the longest-path method.

    Nodes with no predecessors are placed at layer 0.  Every other node is
    placed at 1 + max(layer of predecessors).
    """
    layer: dict[str, int] = {}
    pos_map = {nid: idx for idx, nid in enumerate(topo_order)}

    for nid in topo_order:
        layer[nid] = 0

    # Iterate in topological order; for each edge src->tgt update tgt's layer.
    for src in topo_order:
        for tgt in adj.get(src, []):
            if tgt in node_ids and pos_map.get(tgt, -1) > pos_map.get(src, -1):
                new_layer = layer[src] + 1
                if new_layer > layer.get(tgt, 0):
                    layer[tgt] = new_layer

    return layer


# ---------------------------------------------------------------------------
# Within-layer ordering (barycenter heuristic)
# ---------------------------------------------------------------------------


def _order_layers(
    layers: dict[int, list[str]],
    adj: dict[str, list[str]],
    reverse_adj: dict[str, list[str]],
    passes: int = 4,
) -> dict[int, list[str]]:
    """Reorder nodes within each layer to reduce edge crossings.

    Uses the barycenter heuristic: for each node, compute the average position
    of its neighbours in the adjacent layer, then sort by that value.
    """
    # Build position-in-layer lookup
    pos: dict[str, int] = {}
    for layer_nodes in layers.values():
        for idx, nid in enumerate(layer_nodes):
            pos[nid] = idx

    sorted_layer_keys = sorted(layers.keys())

    for _ in range(passes):
        # Forward sweep (top to bottom)
        for li in sorted_layer_keys[1:]:
            _barycenter_sort(layers[li], reverse_adj, pos)
            for idx, nid in enumerate(layers[li]):
                pos[nid] = idx

        # Backward sweep (bottom to top)
        for li in reversed(sorted_layer_keys[:-1]):
            _barycenter_sort(layers[li], adj, pos)
            for idx, nid in enumerate(layers[li]):
                pos[nid] = idx

    return layers


def _barycenter_sort(
    layer_nodes: list[str],
    neighbour_adj: dict[str, list[str]],
    pos: dict[str, int],
) -> None:
    """Sort *layer_nodes* in-place by barycenter of connected neighbours."""

    def _bary(nid: str) -> float:
        neighbours = neighbour_adj.get(nid, [])
        positions = [pos[n] for n in neighbours if n in pos]
        if not positions:
            return pos.get(nid, 0)
        return sum(positions) / len(positions)

    layer_nodes.sort(key=_bary)


# ---------------------------------------------------------------------------
# Coordinate assignment
# ---------------------------------------------------------------------------


def _assign_coordinates(
    layers: dict[int, list[str]],
    node_map: dict[str, dict[str, Any]],
) -> None:
    """Compute x/y for each node, centering nodes within their layer."""
    if not layers:
        return

    # Find the widest layer to use as centering reference.
    max_layer_width = 0
    for layer_nodes in layers.values():
        width = sum(node_map[nid].get("width", _NODE_WIDTH) for nid in layer_nodes)
        width += _H_SPACING * max(len(layer_nodes) - 1, 0)
        if width > max_layer_width:
            max_layer_width = width

    sorted_keys = sorted(layers.keys())

    for li in sorted_keys:
        layer_nodes = layers[li]
        # Total width of this layer
        total_w = sum(node_map[nid].get("width", _NODE_WIDTH) for nid in layer_nodes)
        total_w += _H_SPACING * max(len(layer_nodes) - 1, 0)

        # Offset to center relative to widest layer
        x_offset = _PADDING + (max_layer_width - total_w) / 2
        y = _PADDING + li * _V_SPACING

        cursor_x = x_offset
        for nid in layer_nodes:
            node = node_map[nid]
            node["x"] = round(cursor_x)
            node["y"] = round(y)
            cursor_x += node.get("width", _NODE_WIDTH) + _H_SPACING


# ---------------------------------------------------------------------------
# Grouping / containers
# ---------------------------------------------------------------------------


def _apply_group_containers(
    spec: dict[str, Any],
    node_map: dict[str, dict[str, Any]],
) -> None:
    """Generate container rectangles for nodes that share a ``group`` value.

    Containers are inserted into ``spec["containers"]`` (created if absent).
    Grouped nodes are nudged so they sit inside their container with padding.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for nid, node in node_map.items():
        g = node.get("group")
        if g:
            groups[g].append(nid)

    if not groups:
        return

    containers: list[dict[str, Any]] = spec.setdefault("containers", [])
    existing_ids = {c.get("id") for c in containers}

    for group_name, member_ids in groups.items():
        if group_name in existing_ids:
            continue

        xs = [node_map[nid]["x"] for nid in member_ids if "x" in node_map[nid]]
        ys = [node_map[nid]["y"] for nid in member_ids if "y" in node_map[nid]]
        if not xs or not ys:
            continue

        rights = [
            node_map[nid]["x"] + node_map[nid].get("width", _NODE_WIDTH) for nid in member_ids if "x" in node_map[nid]
        ]
        bottoms = [
            node_map[nid]["y"] + node_map[nid].get("height", _NODE_HEIGHT) for nid in member_ids if "y" in node_map[nid]
        ]

        cx = min(xs) - _GROUP_PADDING
        cy = min(ys) - _GROUP_PADDING
        cw = max(rights) - min(xs) + _GROUP_PADDING * 2
        ch = max(bottoms) - min(ys) + _GROUP_PADDING * 2

        containers.append(
            {
                "id": group_name,
                "label": group_name,
                "x": round(cx),
                "y": round(cy),
                "width": round(cw),
                "height": round(ch),
            }
        )


# ---------------------------------------------------------------------------
# Auto-sizing
# ---------------------------------------------------------------------------


def _auto_size(spec: dict[str, Any], node_map: dict[str, dict[str, Any]]) -> None:
    """Set spec width/height to fit all positioned content with padding."""
    max_x = 0.0
    max_y = 0.0

    for node in node_map.values():
        if "x" in node and "y" in node:
            r = node["x"] + node.get("width", _NODE_WIDTH)
            b = node["y"] + node.get("height", _NODE_HEIGHT)
            if r > max_x:
                max_x = r
            if b > max_y:
                max_y = b

    for container in spec.get("containers", []):
        r = container.get("x", 0) + container.get("width", 0)
        b = container.get("y", 0) + container.get("height", 0)
        if r > max_x:
            max_x = r
        if b > max_y:
            max_y = b

    spec["width"] = round(max_x + _PADDING)
    spec["height"] = round(max_y + _PADDING)


# ---------------------------------------------------------------------------
# Node defaults
# ---------------------------------------------------------------------------


def _ensure_node_defaults(node: dict[str, Any]) -> None:
    """Set default width/height on a node if not already specified."""
    label = node.get("label", node.get("id", ""))
    if "width" not in node:
        node["width"] = _node_width_for_label(str(label)) if label else _NODE_WIDTH
    if "height" not in node:
        node["height"] = _NODE_HEIGHT


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _layout_group_within_bounds(
    group_ids: set[str],
    arrows: list[dict[str, Any]],
    node_map: dict[str, dict[str, Any]],
    bound_x: float,
    bound_y: float,
    bound_w: float,
    bound_h: float,
    label_reserve: float = 36,
) -> None:
    """Lay out a set of nodes within explicit bounding box coordinates.

    Container layout uses a *horizontal* layer arrangement — topological
    layers map to columns (left → right), nodes within a column stack
    vertically.  This matches the visual convention where a tier container
    is a wide horizontal band.

    Spacing is adaptive so nodes always fit inside the container width and
    height regardless of how many nodes are present.
    """
    if not group_ids:
        return

    pad = _GROUP_PADDING
    inner_x = bound_x + pad
    inner_y = bound_y + label_reserve
    inner_w = max(bound_w - pad * 2, 1.0)
    inner_h = max(bound_h - label_reserve - pad, 1.0)

    adj, in_deg = _build_graph(group_ids, arrows)

    rev_adj: dict[str, list[str]] = defaultdict(list)
    for src, targets in adj.items():
        for tgt in targets:
            if tgt in group_ids:
                rev_adj[tgt].append(src)

    topo = _topological_sort_kahn(group_ids, adj, in_deg)
    layer_of = _assign_layers(topo, adj, group_ids)

    layers: dict[int, list[str]] = defaultdict(list)
    for nid in topo:
        layers[layer_of[nid]].append(nid)

    layers = _order_layers(layers, adj, rev_adj)

    sorted_keys = sorted(layers.keys())

    # --- Horizontal layout: one column per node, ordered by (layer, pos-in-layer) ---
    # This ensures nodes at the same topological level (e.g. 4 peer storage nodes)
    # spread horizontally instead of stacking vertically in one column.
    ordered_nodes: list[str] = []
    for lk in sorted_keys:
        ordered_nodes.extend(layers[lk])

    n_cols = len(ordered_nodes)
    if n_cols == 0:
        return

    # Adaptive column width so all columns fit within inner_w.
    min_col_gap = 20.0
    max_node_w = max((node_map[nid].get("width", _NODE_WIDTH) for nid in ordered_nodes), default=_NODE_WIDTH)
    # Distribute inner_w evenly; each slot = node_width + gap
    slot_w = max(max_node_w, (inner_w - min_col_gap * max(n_cols - 1, 0)) / max(n_cols, 1))
    total_slots_w = slot_w * n_cols + min_col_gap * max(n_cols - 1, 0)
    x_origin = inner_x + max(0.0, (inner_w - total_slots_w) / 2)

    for ci, nid in enumerate(ordered_nodes):
        nw = node_map[nid].get("width", _NODE_WIDTH)
        nh = node_map[nid].get("height", _NODE_HEIGHT)
        col_cx = x_origin + ci * (slot_w + min_col_gap) + slot_w / 2
        node_map[nid]["x"] = round(col_cx - nw / 2)
        node_map[nid]["y"] = round(inner_y + max(0.0, (inner_h - nh) / 2))


def auto_layout(spec: dict[str, Any]) -> dict[str, Any]:
    """Apply auto-layout to nodes missing positions.

    Modifies *spec* in-place and returns it.

    When nodes carry a ``container`` field whose value matches a container
    ``id`` that has explicit ``x``/``y``/``width``/``height``, those nodes
    are laid out *within* the container's bounding box.  All other
    unpositioned nodes fall back to the global Sugiyama-style layout.

    The function handles:
    - Both ``source``/``target`` and ``from``/``to`` arrow key formats
    - Cycles (broken at back-edges via Kahn's algorithm fallback)
    - Default width/height assignment based on label length
    - Container generation for nodes that share a ``group`` property
    - Overall diagram ``width``/``height`` auto-sizing with padding
    """
    nodes: list[dict[str, Any]] = spec.get("nodes", [])
    arrows: list[dict[str, Any]] = spec.get("arrows", [])

    if not nodes:
        return spec

    # Ensure every node has an id, width, and height.
    for node in nodes:
        _ensure_node_defaults(node)

    # Determine which nodes still need positioning.
    needs_layout = [n for n in nodes if "x" not in n or "y" not in n]
    if not needs_layout:
        node_map = {n["id"]: n for n in nodes if "id" in n}
        _apply_group_containers(spec, node_map)
        _auto_size(spec, node_map)
        return spec

    # Build id -> node lookup (all nodes).
    node_map: dict[str, dict[str, Any]] = {n["id"]: n for n in nodes if "id" in n}

    # Build a lookup of containers that have explicit bounds.
    containers_spec: list[dict[str, Any]] = spec.get("containers", [])
    bounded_containers: dict[str, dict[str, Any]] = {
        c["id"]: c for c in containers_spec if "id" in c and "x" in c and "y" in c and "width" in c and "height" in c
    }

    # Identify the set of node ids that need layout.
    layout_ids: set[str] = {n["id"] for n in needs_layout if "id" in n}

    # ----- Container-aware layout -----
    # Group unpositioned nodes by their declared container.
    container_groups: dict[str, list[str]] = defaultdict(list)
    global_ids: list[str] = []

    for nid in layout_ids:
        cid = node_map[nid].get("container")
        if cid and cid in bounded_containers:
            container_groups[cid].append(nid)
        else:
            global_ids.append(nid)

    # Lay out each container group within its bounds.
    for cid, group_node_ids in container_groups.items():
        c = bounded_containers[cid]
        _layout_group_within_bounds(
            group_ids=set(group_node_ids),
            arrows=arrows,
            node_map=node_map,
            bound_x=c["x"],
            bound_y=c["y"],
            bound_w=c["width"],
            bound_h=c["height"],
        )

    # ----- Global layout for nodes without a container -----
    if global_ids:
        global_id_set = set(global_ids)

        existing_max_y = 0.0
        if len(global_id_set) < len(nodes):
            for node in nodes:
                if "x" in node and "y" in node:
                    bottom = node["y"] + node.get("height", _NODE_HEIGHT)
                    if bottom > existing_max_y:
                        existing_max_y = bottom
            existing_max_y += _V_SPACING

        adj, in_deg = _build_graph(global_id_set, arrows)

        rev_adj: dict[str, list[str]] = defaultdict(list)
        for src, targets in adj.items():
            for tgt in targets:
                if tgt in global_id_set:
                    rev_adj[tgt].append(src)

        topo = _topological_sort_kahn(global_id_set, adj, in_deg)
        layer_of = _assign_layers(topo, adj, global_id_set)

        layers: dict[int, list[str]] = defaultdict(list)
        for nid in topo:
            layers[layer_of[nid]].append(nid)

        layers = _order_layers(layers, adj, rev_adj)
        _assign_coordinates(layers, node_map)

        if existing_max_y > 0:
            for nid in global_id_set:
                node = node_map[nid]
                if "y" in node:
                    node["y"] = round(node["y"] + existing_max_y)

    # ----- Containers for grouped nodes (group property) -----
    _apply_group_containers(spec, node_map)

    # ----- Auto-size the diagram -----
    _auto_size(spec, node_map)

    return spec
