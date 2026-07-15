from __future__ import annotations

import os
import shlex
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Renderer:
    id: str
    command: list[str]
    timing_scope: str
    environment: dict[str, str]


@dataclass(frozen=True)
class Case:
    id: str
    html: Path
    tags: tuple[str, ...]
    required_text: tuple[str, ...]
    min_pages: int | None
    max_pages: int | None


@dataclass(frozen=True)
class Profile:
    cases: tuple[str, ...]
    warmups: int
    iterations: int
    dpi: int


@dataclass(frozen=True)
class Config:
    path: Path
    reference: str
    candidates: tuple[str, ...]
    renderers: dict[str, Renderer]
    cases: dict[str, Case]
    profiles: dict[str, Profile]
    weights: dict[str, float]
    budgets: dict[str, float]
    output_root: Path
    history_limit: int


def _expand(value: str) -> str:
    return os.path.expandvars(value)


def load(path: Path) -> Config:
    path = path.resolve()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    renderer_values = {}
    for raw_id, value in raw.get("renderers", {}).items():
        rid = _expand(raw_id)
        command = value.get("command", [])
        if isinstance(command, str):
            command = shlex.split(command, posix=os.name != "nt")
        renderer_values[rid] = Renderer(
            rid,
            [_expand(str(part)) for part in command],
            value.get("timing_scope", "process"),
            {key: _expand(str(item)) for key, item in value.get("environment", {}).items()},
        )
    case_values = {}
    for cid, value in raw.get("cases", {}).items():
        html = Path(_expand(value["html"]))
        if not html.is_absolute():
            html = root / html
        case_values[cid] = Case(
            cid, html.resolve(), tuple(value.get("tags", [])), tuple(value.get("required_text", [])),
            value.get("min_pages"), value.get("max_pages"),
        )
    profiles = {
        name: Profile(tuple(value.get("cases", [])), int(value.get("warmups", 1)),
                      int(value.get("iterations", 5)), int(value.get("dpi", 144)))
        for name, value in raw.get("profiles", {}).items()
    }
    comparison = raw.get("comparison", {})
    output = raw.get("output", {})
    output_root = Path(_expand(output.get("root", ".bench")))
    if not output_root.is_absolute():
        output_root = root / output_root
    return Config(
        path, _expand(comparison.get("reference", "")),
        tuple(_expand(item) for item in comparison.get("candidates", [])),
        renderer_values, case_values, profiles,
        raw.get("scoring", {}).get("weights", {name: 1 for name in ("text", "layout", "pagination", "assets", "visual")}),
        {key: float(value) for key, value in raw.get("budgets", {}).items()},
        output_root.resolve(), int(output.get("history_limit", 20)),
    )


def validate(config: Config, require_commands: bool = False) -> list[str]:
    errors = []
    if config.reference not in config.renderers:
        errors.append("comparison.reference must name a renderer")
    for candidate in config.candidates:
        if candidate not in config.renderers:
            errors.append(f"unknown candidate renderer: {candidate}")
    if not config.candidates:
        errors.append("at least one candidate renderer is required")
    for renderer in config.renderers.values():
        if not renderer.command:
            errors.append(f"renderer {renderer.id} has no command")
        elif require_commands and not _command_exists(renderer.command[0]):
            errors.append(f"renderer command not found: {renderer.command[0]}")
        if renderer.timing_scope not in {"process", "warm-engine", "adapter-defined"}:
            errors.append(f"renderer {renderer.id} has invalid timing_scope")
    for case in config.cases.values():
        if not case.html.is_file():
            errors.append(f"case {case.id} HTML not found: {case.html}")
    for name, profile in config.profiles.items():
        if profile.iterations < 1 or profile.warmups < 0 or profile.dpi < 36:
            errors.append(f"profile {name} has invalid timing or DPI values")
        for case in profile.cases:
            if case not in config.cases:
                errors.append(f"profile {name} references unknown case: {case}")
    if not config.profiles:
        errors.append("at least one profile is required")
    if sum(config.weights.values()) <= 0:
        errors.append("scoring weights must have a positive total")
    return errors


def _command_exists(command: str) -> bool:
    from shutil import which
    value = Path(command)
    return value.is_file() if value.is_absolute() or value.parent != Path(".") else which(command) is not None
