"""
Minimal YAML loader/dumper for the test fixtures.

This is intentionally lightweight and only supports the small subset of YAML
used in this repository (nested mappings, string scalars, simple lists).
It is **not** a full YAML parser, but it is sufficient for config files in
tests and stack templates without requiring the external PyYAML dependency.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _strip_quotes(value: str) -> str:
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        try:
            return int(value)
        except ValueError:
            pass
    try:
        return float(value)
    except ValueError:
        pass
    return _strip_quotes(value)


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: List[str], idx: int, indent: int) -> Tuple[Any, int]:
    # Skip blank/comment lines
    while idx < len(lines) and (not lines[idx].strip() or lines[idx].lstrip().startswith("#")):
        idx += 1
    if idx >= len(lines):
        return {}, idx

    current_indent = _leading_spaces(lines[idx])
    if current_indent < indent:
        return {}, idx

    first_content = lines[idx][current_indent:]
    if first_content.startswith("- "):
        items: List[Any] = []
        while idx < len(lines):
            line = lines[idx]
            if not line.strip() or line.lstrip().startswith("#"):
                idx += 1
                continue
            line_indent = _leading_spaces(line)
            if line_indent < indent or not line[line_indent:].startswith("- "):
                break

            item_body = line[line_indent + 2 :].rstrip()
            idx += 1

            # Empty body: nested structure follows.
            if not item_body:
                value, idx = _parse_block(lines, idx, line_indent + 2)
                items.append(value)
                continue

            # Mapping-style list item (e.g., "- name: foo" plus more fields)
            if ":" in item_body:
                key, _, rest = item_body.partition(":")
                rest = rest.strip()
                item: Dict[str, Any] = {}
                if rest:
                    item[key.strip()] = _parse_scalar(rest)
                else:
                    value, idx = _parse_block(lines, idx, line_indent + 2)
                    item[key.strip()] = value

                # Consume additional mapping lines indented beneath this list item.
                while idx < len(lines):
                    peek = lines[idx]
                    if not peek.strip() or peek.lstrip().startswith("#"):
                        idx += 1
                        continue
                    peek_indent = _leading_spaces(peek)
                    if peek_indent <= line_indent or peek[peek_indent:].startswith("- "):
                        break
                    content = peek[peek_indent:]
                    k, _, r = content.partition(":")
                    k = k.strip()
                    r = r.strip()
                    if r:
                        item[k] = _parse_scalar(r)
                        idx += 1
                    else:
                        idx += 1
                        val, idx = _parse_block(lines, idx, peek_indent + 2)
                        item[k] = val
                items.append(item)
                continue

            # Scalar list item
            items.append(_parse_scalar(item_body))
        return items, idx

    mapping: Dict[str, Any] = {}
    while idx < len(lines):
        line = lines[idx]
        if not line.strip() or line.lstrip().startswith("#"):
            idx += 1
            continue
        line_indent = _leading_spaces(line)
        if line_indent < indent:
            break
        content = line[line_indent:]
        if content.startswith("- "):
            # Switch to list parsing at this indent level
            value, idx = _parse_block(lines, idx, line_indent)
            return value, idx
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest:
            mapping[key] = _parse_scalar(rest)
            idx += 1
        else:
            idx += 1
            value, idx = _parse_block(lines, idx, line_indent + 2)
            mapping[key] = value
    return mapping, idx


def safe_load(stream: str | None) -> Any:
    if stream is None:
        return None
    lines = stream.splitlines()
    parsed, _ = _parse_block(lines, 0, 0)
    return parsed


def _dump(obj: Any, indent: int) -> List[str]:
    prefix = " " * indent
    if isinstance(obj, dict):
        lines: List[str] = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_dump(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_strip_quotes(str(value)) if isinstance(value, str) else value}")
        return lines
    if isinstance(obj, list):
        lines = []
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_dump(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_strip_quotes(str(item)) if isinstance(item, str) else item}")
        return lines
    return [f"{prefix}{_strip_quotes(str(obj))}"]


def safe_dump(data: Any, *_, **__) -> str:
    lines = _dump(data, 0)
    return "\n".join(lines) + ("\n" if lines else "")


dump = safe_dump
load = safe_load
