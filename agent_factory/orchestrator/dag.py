from __future__ import annotations

from typing import Dict, List, Set


class DagError(Exception):
    pass


def topo_sort(tasks: List[Dict]) -> List[Dict]:
    by_id = {t["id"]: t for t in tasks}
    deps = {t["id"]: set(t.get("depends_on") or []) for t in tasks}

    # validate
    for tid, d in deps.items():
        for x in d:
            if x not in by_id:
                raise DagError(f"Task {tid} depends on missing task {x}")

    out: List[Dict] = []
    ready = [tid for tid, d in deps.items() if not d]
    ready.sort()

    while ready:
        tid = ready.pop(0)
        out.append(by_id[tid])

        for other, d in deps.items():
            if tid in d:
                d.remove(tid)
                already_scheduled = any(t["id"] == other for t in out)
                if not d and other not in ready and not already_scheduled:
                    ready.append(other)
                    ready.sort()

    if len(out) != len(tasks):
        raise DagError("Cycle detected in task dependencies")
    return out
