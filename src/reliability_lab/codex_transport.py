"""Optional host-only benchmark transport; not required by the Docker application."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def complete(system, user, schema, model):
    executable = shutil.which("codex")
    if not executable:
        raise RuntimeError("Codex CLI is not installed; use HTTP transport in Docker")
    with tempfile.TemporaryDirectory(prefix="reliability-inference-") as folder:
        root = Path(folder)
        schema_path, output = root / "schema.json", root / "answer.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        command = [
            executable,
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--cd",
            folder,
            "--disable",
            "shell_tool",
            "--disable",
            "unified_exec",
            "-c",
            'web_search="disabled"',
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output),
            "--json",
        ]
        if model != "codex-default":
            command += ["--model", model]
        command += ["-"]
        result = subprocess.run(
            command,
            input=system + "\nUse no tools. Answer only from the supplied context.\n" + user,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=float(os.getenv("LAB_MODEL_TIMEOUT", "180")),
            check=False,
        )
        if result.returncode or not output.exists():
            raise RuntimeError(
                "Headless inference failed; check local Codex sign-in and model availability"
            )
        usage = {}
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "turn.completed":
                raw = event.get("usage", {})
                usage = {
                    "prompt_tokens": raw.get("input_tokens", 0),
                    "completion_tokens": raw.get("output_tokens", 0),
                    "total_tokens": raw.get("input_tokens", 0) + raw.get("output_tokens", 0),
                }
            if event.get("type") == "item.completed" and event.get("item", {}).get("type") in {
                "command_execution",
                "mcp_tool_call",
                "web_search",
                "file_change",
            }:
                raise RuntimeError("Benchmark rejected: inference attempted a tool action")
        return output.read_text(encoding="utf-8"), usage
