from __future__ import annotations

import dataclasses
import enum
import json
from typing import Any

from ast_nodes import Node, SourceSpan


def format_ast(node: Node, *, show_spans: bool = False) -> str:
    """Produza uma árvore legível no terminal.

    A travessia usa os campos dos dataclasses, portanto acompanha novos tipos
    de nó sem exigir uma sequência de ``isinstance``.
    """

    lines = [type(node).__name__]
    _append_tree(lines, node, prefix="", show_spans=show_spans)
    return "\n".join(lines)


def _append_tree(
    lines: list[str],
    node: Node,
    *,
    prefix: str,
    show_spans: bool,
) -> None:
    entries = _tree_entries(node, show_spans=show_spans)
    for index, (label, child) in enumerate(entries):
        is_last = index == len(entries) - 1
        branch = "└── " if is_last else "├── "
        lines.append(f"{prefix}{branch}{label}")
        if child is not None:
            continuation = "    " if is_last else "│   "
            _append_tree(
                lines,
                child,
                prefix=prefix + continuation,
                show_spans=show_spans,
            )


def _tree_entries(node: Node, *, show_spans: bool) -> list[tuple[str, Node | None]]:
    entries: list[tuple[str, Node | None]] = []
    if show_spans:
        entries.append((f"span: {_format_value(node.span)}", None))

    for field in dataclasses.fields(node):
        if field.name in {"span", "metadata"}:
            continue
        value = getattr(node, field.name)
        if isinstance(value, Node):
            entries.append((f"{field.name}: {type(value).__name__}", value))
        elif isinstance(value, list):
            if not value:
                entries.append((f"{field.name}: []", None))
            else:
                for index, item in enumerate(value):
                    if isinstance(item, Node):
                        entries.append(
                            (f"{field.name}[{index}]: {type(item).__name__}", item)
                        )
                    else:
                        entries.append((f"{field.name}[{index}]: {_format_value(item)}", None))
        else:
            entries.append((f"{field.name}: {_format_value(value)}", None))
    return entries


def ast_to_dot(node: Node, *, show_spans: bool = False) -> str:
    """Produza um grafo Graphviz DOT da AST, sem depender do Graphviz."""

    lines = [
        "digraph AST {",
        "  rankdir=TB;",
        '  graph [bgcolor="white", pad=0.2, nodesep=0.35, ranksep=0.55];',
        '  node [shape=box, style="rounded,filled", fillcolor="#EAF2F8",',
        '        color="#246A9A", fontname="monospace"];',
        '  edge [color="#667788", fontname="monospace", fontsize=10];',
    ]
    next_id = 0

    def visit(current: Node) -> str:
        nonlocal next_id
        node_id = f"n{next_id}"
        next_id += 1

        label_parts = [type(current).__name__]
        if show_spans:
            label_parts.append(f"span = {_format_value(current.span)}")

        children: list[tuple[str, Node]] = []
        for field in dataclasses.fields(current):
            if field.name in {"span", "metadata"}:
                continue
            value = getattr(current, field.name)
            if isinstance(value, Node):
                children.append((field.name, value))
            elif isinstance(value, list):
                if not value:
                    label_parts.append(f"{field.name} = []")
                for index, item in enumerate(value):
                    if isinstance(item, Node):
                        children.append((f"{field.name}[{index}]", item))
                    else:
                        label_parts.append(
                            f"{field.name}[{index}] = {_format_value(item)}"
                        )
            else:
                label_parts.append(f"{field.name} = {_format_value(value)}")

        label = "\n".join(label_parts)
        lines.append(f"  {node_id} [label={_dot_quote(label)}];")
        for edge_label, child in children:
            child_id = visit(child)
            lines.append(
                f"  {node_id} -> {child_id} [label={_dot_quote(edge_label)}];"
            )
        return node_id

    visit(node)
    lines.append("}")
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if isinstance(value, enum.Enum):
        return str(value.value)
    if isinstance(value, SourceSpan):
        return (
            f"{value.start_line}:{value.start_column}"
            f"–{value.end_line}:{value.end_column}"
        )
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return "none"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _dot_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
