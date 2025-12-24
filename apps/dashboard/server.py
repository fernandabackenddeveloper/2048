from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS = (REPO_ROOT / "runs").resolve()


def read_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            html = (REPO_ROOT / "apps/dashboard/index.html").read_text(encoding="utf-8")
            return self._send(200, html, "text/html")

        if path == "/api/runs":
            items = []
            for d in sorted(RUNS.glob("*")):
                if not d.is_dir():
                    continue
                items.append(
                    {
                        "project": d.name,
                        "state": read_json(d / "state.json", {}),
                        "final": read_json(d / "reports/final_report.json", {}),
                    }
                )
            return self._send(200, json.dumps(items, ensure_ascii=False))

        if path.startswith("/api/run/"):
            project = path.split("/api/run/")[1].strip("/")
            root = RUNS / project
            data = {
                "project": project,
                "plan": read_json(root / "plan.json", {}),
                "state": read_json(root / "state.json", {}),
                "final": read_json(root / "reports/final_report.json", {}),
            }
            return self._send(200, json.dumps(data, ensure_ascii=False))

        if path.startswith("/api/run/") and path.endswith("/sandboxes"):
            project = path.split("/api/run/")[1].split("/sandboxes")[0].strip("/")
            root = RUNS / project
            sand = root / "sandboxes"
            items = []
            if sand.exists():
                for d in sorted(sand.iterdir()):
                    if not d.is_dir():
                        continue
                    art = d / "runs" / project / "artifacts"
                    items.append(
                        {
                            "task": d.name,
                            "sandbox": str(d),
                            "artifacts": {
                                "tests_diff": str(art / f"{d.name}_tests.diff") if (art / f"{d.name}_tests.diff").exists() else None,
                                "code_diff": str(art / f"{d.name}_code.diff") if (art / f"{d.name}_code.diff").exists() else None,
                                "changes": str(art / f"changes_{d.name}.json") if (art / f"changes_{d.name}.json").exists() else None,
                            },
                        }
                    )
            return self._send(200, json.dumps(items, ensure_ascii=False))

        if "/api/diff/" in path:
            parts = path.strip("/").split("/")
            if len(parts) >= 5:
                _, _, project, task, kind = parts[:5]
                base = RUNS / project / "sandboxes" / task / "runs" / project / "artifacts"
                target = None
                if kind in {"tests", "code"}:
                    target = base / f"{task}_{kind}.diff"
                elif kind == "changes":
                    target = base / f"changes_{task}.json"
                if target and target.exists():
                    ctype = "application/json" if target.suffix == ".json" else "text/plain"
                    return self._send(200, target.read_text(encoding="utf-8"), ctype)
            return self._send(404, json.dumps({"error": "not found"}))

        return self._send(404, json.dumps({"error": "not found"}))


def main() -> None:
    srv = HTTPServer(("127.0.0.1", 8787), Handler)
    print("Dashboard: http://127.0.0.1:8787")
    srv.serve_forever()


if __name__ == "__main__":
    main()
