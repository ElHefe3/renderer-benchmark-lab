from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
from pathlib import Path

from .config import load, validate
from .report import generate
from .runner import approve, run


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="renderer-bench")
    value.add_argument("--config", type=Path, default=Path("benchmark.toml"))
    commands = value.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate")
    check.add_argument("--require-commands", action="store_true")
    execute = commands.add_parser("run")
    execute.add_argument("--profile", default="full")
    report = commands.add_parser("report")
    report.add_argument("--output", type=Path)
    baseline = commands.add_parser("baseline")
    baseline.add_argument("action", choices=["approve"])
    baseline.add_argument("run_id")
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8000)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = load(args.config)
    errors = validate(config, getattr(args, "require_commands", False))
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print(f"valid: {config.path}")
        return 0
    if args.command == "run":
        if args.profile not in config.profiles:
            print(f"error: unknown profile {args.profile}", file=sys.stderr)
            return 2
        root, manifest = run(config, args.profile)
        output = generate(config)
        print(root)
        print(output / "index.html")
        return 1 if manifest["status"] == "failed" else 0
    if args.command == "report":
        print(generate(config, args.output))
        return 0
    if args.command == "baseline":
        print(approve(config, args.run_id))
        return 0
    output = generate(config)
    def handler(*values, **kwargs):
        return http.server.SimpleHTTPRequestHandler(*values, directory=str(output), **kwargs)
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Dashboard: http://127.0.0.1:{args.port}/")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
