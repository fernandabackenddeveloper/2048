from __future__ import annotations

from typing import Callable, Iterable, List

from agent_factory.orchestrator.task_graph import Task


class TaskRouter:
    """Executes tasks sequentially, respecting dependency ordering."""

    def __init__(self, tasks: Iterable[Task]):
        self.tasks: List[Task] = list(tasks)

    def run(self, runner: Callable[[Task], None]) -> None:
        completed = set()
        pending = {task.id for task in self.tasks}
        task_map = {task.id: task for task in self.tasks}

        while pending:
            progress_made = False
            for task_id in list(pending):
                task = task_map[task_id]
                if all(dep in completed for dep in task.depends_on):
                    runner(task)
                    completed.add(task_id)
                    pending.remove(task_id)
                    progress_made = True
            if not progress_made:
                raise RuntimeError(
                    f"Circular or unsatisfied dependencies detected: {sorted(pending)}"
                )
