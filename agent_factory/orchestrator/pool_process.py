from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Set


@dataclass
class PoolResult:
    task_id: str
    result: Dict[str, Any]


def _changed_set(res: Dict[str, Any]) -> Set[str]:
    ch = res.get("changes") or {}
    return set(ch.get("created", [])) | set(ch.get("deleted", [])) | set(ch.get("modified", []))


def schedule_batches(tasks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Greedy batching: tasks in same batch must have disjoint 'touch_hints' sets if present.
    If no hints, they can run together.
    """
    batches: List[List[Dict[str, Any]]] = []
    for t in tasks:
        hint = set(t.get("touch_hints") or [])
        placed = False
        for b in batches:
            used = set()
            for x in b:
                used |= set(x.get("touch_hints") or [])
            if used.isdisjoint(hint):
                b.append(t)
                placed = True
                break
        if not placed:
            batches.append([t])
    return batches


def run_process_pool(
    batch: List[Dict[str, Any]],
    worker_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    max_workers: int = 2,
) -> List[PoolResult]:
    results: List[PoolResult] = []
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(worker_fn, t): t for t in batch}
        for fut in as_completed(fut_map):
            task = fut_map[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"task": task["id"], "status": "failed", "error": str(e)}
            results.append(PoolResult(task_id=task["id"], result=res))
    return results
