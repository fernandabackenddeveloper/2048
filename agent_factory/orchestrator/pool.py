from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class PoolResult:
    task_id: str
    result: Dict[str, Any]


def run_pool(
    tasks: List[Dict[str, Any]],
    worker_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    max_workers: int = 2,
) -> List[PoolResult]:
    """
    Runs tasks concurrently and returns results (unordered).
    Keep merges out of worker_fn if you want conflict-free fan-in.
    """
    results: List[PoolResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(worker_fn, t): t for t in tasks}
        for fut in as_completed(fut_map):
            task = fut_map[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"task": task["id"], "status": "failed", "error": str(e)}
            results.append(PoolResult(task_id=task["id"], result=res))
    return results
