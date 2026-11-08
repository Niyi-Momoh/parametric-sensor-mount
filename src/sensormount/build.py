"""Run OpenSCAD and load its output."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import trimesh

SCAD_FILE = Path(__file__).parents[2] / "scad" / "mount.scad"
PARTS = ("bracket", "cradle", "servo", "sensor", "beam")
_INFO = re.compile(r'ECHO: "INFO (\w+)=([-\d.e]+)"')


class ScadError(RuntimeError):
    """Raised when OpenSCAD rejects the design."""


def _definitions(values: Mapping[str, object]) -> list[str]:
    arguments: list[str] = []
    for name, value in values.items():
        text = f'"{value}"' if isinstance(value, str) else str(value)
        arguments += ["-D", f"{name}={text}"]
    return arguments


def run_openscad(output: Path, values: Mapping[str, object]) -> dict[str, float]:
    """Export one file and return the design values reported by the model."""
    command = ["openscad", "-o", str(output), *_definitions(values), str(SCAD_FILE)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    log = result.stdout + result.stderr
    if result.returncode != 0 or "ERROR" in log or "WARNING: Object may not be a valid" in log:
        raise ScadError(log.strip())
    return {name: float(value) for name, value in _INFO.findall(log)}


@dataclass(frozen=True)
class Model:
    meshes: dict[str, trimesh.Trimesh]
    info: dict[str, float]


def build_model(folder: Path, overrides: Mapping[str, object] | None = None) -> Model:
    """Export every part as an STL file and load the results."""
    folder.mkdir(parents=True, exist_ok=True)
    meshes: dict[str, trimesh.Trimesh] = {}
    info: dict[str, float] = {}
    for part in PARTS:
        path = folder / f"{part}.stl"
        info = run_openscad(path, {**(overrides or {}), "part": part})
        meshes[part] = trimesh.load_mesh(path)
    return Model(meshes, info)
