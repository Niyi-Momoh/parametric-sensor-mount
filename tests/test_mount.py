from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import trimesh

from sensormount.analysis import (
    insertion_overlap,
    interference,
    pose,
    print_mass_g,
    sweep,
    torque_estimate,
)
from sensormount.build import ScadError, build_model, run_openscad

ROOT = Path(__file__).parents[1]
PRINT_PARTS = ("bracket", "cradle")
BED_MM = (220, 220, 250)


@pytest.fixture(scope="session")
def model(tmp_path_factory):
    return build_model(tmp_path_factory.mktemp("stl"))


@pytest.mark.parametrize("part", PRINT_PARTS)
def test_printed_parts_are_valid_single_solids(model, part):
    mesh = model.meshes[part]
    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    assert mesh.volume > 0
    assert len(mesh.split(only_watertight=True)) == 1


@pytest.mark.parametrize("part", PRINT_PARTS)
def test_printed_parts_fit_a_common_print_bed_and_sit_flat(model, part):
    mesh = model.meshes[part]
    assert all(size < limit for size, limit in zip(mesh.extents, BED_MM, strict=True))
    assert mesh.bounds[0][2] == pytest.approx(0, abs=1e-6)


def test_servo_seats_in_bracket(model):
    assert interference(model.meshes["servo"], model.meshes["bracket"]) < 1.0


def test_sensor_seats_in_cradle(model):
    assert interference(model.meshes["sensor"], model.meshes["cradle"]) < 1e-6


def test_servo_can_be_lowered_into_place(model):
    assert insertion_overlap(model.meshes["servo"], model.meshes["bracket"], 32) < 1.0


def test_sensor_can_slide_down_the_groove(model):
    assert insertion_overlap(model.meshes["sensor"], model.meshes["cradle"], 32) < 1e-6


def test_no_collision_through_full_pan_range(model):
    result = sweep(model)
    assert result["overlap_mm3"] < 1e-6
    assert result["min_gap_mm"] > 0.5


def test_collision_check_detects_a_deliberate_clash(model):
    placed = pose(model.meshes["cradle"], model.info["cradle_z"] - 12, 0)
    assert interference(placed, model.meshes["servo"]) > 1.0


def test_ultrasonic_beams_are_unobstructed(model):
    assert interference(model.meshes["beam"], model.meshes["cradle"]) < 1e-6


def test_servo_has_ample_torque_margin(model):
    assert torque_estimate(model)["share_of_rated"] < 0.5


@pytest.mark.parametrize(
    "overrides",
    [
        {"clearance": 0.1},
        {"clearance": 0.6},
        {"wall": 2.0},
        {"wall": 5.0},
        {"chassis_hole_x": 22},
        {"hub_thickness": 7},
        {"board_fit": 0.5},
    ],
)
def test_design_stays_valid_when_parameters_change(tmp_path, overrides):
    built = build_model(tmp_path, overrides)
    for part in PRINT_PARTS:
        assert built.meshes[part].is_watertight
        assert len(built.meshes[part].split(only_watertight=True)) == 1
    assert interference(built.meshes["sensor"], built.meshes["cradle"]) < 1e-6
    assert interference(built.meshes["servo"], built.meshes["bracket"]) < 1.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"wall": 1.0},
        {"clearance": 2},
        {"board_width": 42},
        {"groove_depth": 1},
        {"frame_offset": 10},
    ],
)
def test_unsafe_parameters_are_rejected(tmp_path, overrides):
    with pytest.raises(ScadError):
        run_openscad(tmp_path / "x.stl", {**overrides, "part": "bracket"})


def test_print_mass_uses_shells_and_infill():
    cube = trimesh.creation.box((100, 100, 100))
    solid = cube.volume / 1000 * 1.24
    assert 0.2 * solid < print_mass_g(cube) < solid


@pytest.mark.parametrize("part", PRINT_PARTS)
def test_committed_stl_matches_the_model(model, part):
    committed = trimesh.load_mesh(ROOT / "stl" / f"{part}.stl")
    assert committed.volume == pytest.approx(model.meshes[part].volume, rel=1e-6)


def test_readme_results_match_the_report():
    spec = importlib.util.spec_from_file_location("report", ROOT / "scripts" / "report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    study = json.loads((ROOT / "results" / "report.json").read_text())
    assert module.block(study) in (ROOT / "README.md").read_text()
