from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class BudgetState:
    inflight: int = 0
    fixes_used: int = 0


@dataclass
class BudgetManager:
    budgets: Dict[str, Dict[str, Any]]
    state: Dict[str, BudgetState] = field(default_factory=dict)

    def _st(self, cap: str) -> BudgetState:
        self.state.setdefault(cap, BudgetState())
        return self.state[cap]

    def can_start(self, cap: str) -> bool:
        lim = int(self.budgets.get(cap, {}).get("max_tasks_inflight", 5))
        return self._st(cap).inflight < lim

    def started(self, cap: str) -> None:
        self._st(cap).inflight += 1

    def finished(self, cap: str) -> None:
        self._st(cap).inflight = max(0, self._st(cap).inflight - 1)

    def can_fix(self, cap: str) -> bool:
        lim = int(self.budgets.get(cap, {}).get("max_fix_attempts", 6))
        return self._st(cap).fixes_used < lim

    def used_fix(self, cap: str) -> None:
        self._st(cap).fixes_used += 1
