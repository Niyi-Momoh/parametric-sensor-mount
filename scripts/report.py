"""Build the STL files, run every check and update the README."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

START = "<!-- results:start -->"
END = "<!-- results:end -->"
MIN_GAP = 0.5


def render(study: dict) -> str:
    sweep = study["sweep"]
    torque = study["torque"]
    verdict = lambda ok: "Pass" if ok else "Fail"  # noqa: E731
    parts = study["parts"]
    rows = [
        (
            "Printed parts are single watertight solids",
            "2 of 2" if study["valid"] else "Failed",
            study["valid"],
        ),
        (
            "Servo body fits the bracket pocket",
            f"{study['servo_overlap_mm3']:.3f} mm³ overlap",
            study["servo_overlap_mm3"] < 1,
        ),
        (
            "Sensor fits and slides down the groove",
            f"{study['sensor_slide_mm3']:.3f} mm³ overlap",
            study["sensor_slide_mm3"] < 1e-6,
        ),
        (
            f"No collision from -90° to +90° ({sweep['angles']} angles checked)",
            f"{sweep['overlap_mm3']:.3f} mm³ overlap",
            sweep["overlap_mm3"] < 1e-6,
        ),
        (
            f"Moving and fixed parts stay at least {MIN_GAP} mm apart",
            f"{sweep['min_gap_mm']:.2f} mm",
            sweep["min_gap_mm"] >= MIN_GAP,
        ),
        (
            "15° ultrasonic beams are unobstructed",
            f"{study['beam_overlap_mm3']:.3f} mm³ overlap",
            study["beam_overlap_mm3"] < 1e-6,
        ),
    ]
    lines = ["| Automated check | Measured | Result |", "|---|---:|---|"]
    lines += [f"| {name} | {value} | {verdict(ok)} |" for name, value, ok in rows]
    lines += [
        "",
        "| Part | Size (mm) | Estimated PLA |",
        "|---|---:|---:|",
    ]
    for name, item in parts.items():
        size = " x ".join(f"{value:.1f}" for value in item["size_mm"])
        lines.append(f"| {name.capitalize()} | {size} | {item['mass_g']:.1f} g |")
    lines += [
        "",
        f"Estimated peak load for a 60° move in 0.1 s: {torque['peak_torque_nm'] * 1000:.1f} mN m, "
        f"or {torque['share_of_rated'] * 100:.1f}% of a typical SG90 rating.",
    ]
    return "\n".join(lines)


def block(study: dict) -> str:
    return f"{START}\n{render(study)}\n{END}"


def screenshot(output: str, rotation: str, values: tuple[str, ...]) -> None:
    subprocess.run(
        [
            "xvfb-run",
            "-a",
            "openscad",
            "-o",
            output,
            "--imgsize=1400,1000",
            f"--camera=0,0,0,{rotation},0",
            "--viewall",
            "--autocenter",
            "--colorscheme=Tomorrow",
            "--projection=p",
            *values,
            "scad/mount.scad",
        ],
        check=True,
        capture_output=True,
        timeout=300,
    )


def main() -> None:
    from sensormount.analysis import (
        insertion_overlap,
        interference,
        print_mass_g,
        sweep,
        torque_estimate,
    )
    from sensormount.build import build_model

    model = build_model(Path("stl"))
    for extra in ("servo", "sensor", "beam"):
        Path(f"stl/{extra}.stl").unlink()
    meshes = model.meshes
    study = {
        "valid": all(
            meshes[p].is_watertight and len(meshes[p].split(only_watertight=True)) == 1
            for p in ("bracket", "cradle")
        ),
        "servo_overlap_mm3": max(
            interference(meshes["servo"], meshes["bracket"]),
            insertion_overlap(meshes["servo"], meshes["bracket"], 32),
        ),
        "sensor_slide_mm3": insertion_overlap(meshes["sensor"], meshes["cradle"], 32),
        "beam_overlap_mm3": interference(meshes["beam"], meshes["cradle"]),
        "sweep": sweep(model),
        "torque": torque_estimate(model),
        "parts": {
            p: {
                "size_mm": [float(v) for v in meshes[p].extents],
                "mass_g": print_mass_g(meshes[p]),
            }
            for p in ("bracket", "cradle")
        },
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/report.json").write_text(json.dumps(study, indent=1))
    screenshot("results/assembly.png", "68,0,150", ("-D", "angle=20"))
    screenshot("results/cradle.png", "62,0,335", ("--render", "-D", 'part="cradle"'))
    readme = Path("README.md")
    readme.write_text(
        re.sub(
            re.escape(START) + ".*?" + re.escape(END),
            lambda _: block(study),
            readme.read_text(),
            flags=re.S,
        )
    )
    print(json.dumps(study, indent=1))


if __name__ == "__main__":
    main()
