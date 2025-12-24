from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CapabilityScheduler:
    concurrency: Dict[str, int]
    running: Dict[str, int] = field(default_factory=dict)

    def can_run(self, cap: str) -> bool:
        self.running.setdefault(cap, 0)
        return self.running[cap] < int(self.concurrency.get(cap, 1))

    def start(self, cap: str) -> None:
        self.running[cap] = self.running.get(cap, 0) + 1

    def finish(self, cap: str) -> None:
        self.running[cap] = max(0, self.running.get(cap, 0) - 1)
