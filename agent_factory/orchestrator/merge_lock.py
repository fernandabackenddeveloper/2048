from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MergeLock:
    lockfile: Path
    timeout_s: int = 60

    def acquire(self) -> None:
        start = time.time()
        while True:
            try:
                self.lockfile.parent.mkdir(parents=True, exist_ok=True)
                fd = self.lockfile.open("x")
                fd.write("locked")
                fd.close()
                return
            except FileExistsError:
                if time.time() - start > self.timeout_s:
                    raise TimeoutError("Merge lock timeout")
                time.sleep(0.2)

    def release(self) -> None:
        self.lockfile.unlink(missing_ok=True)
