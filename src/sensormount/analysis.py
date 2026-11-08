"""Check that the parts can be printed, assembled and moved."""

from __future__ import annotations

import math

import numpy as np
import trimesh

PLA_G_PER_CM3 = 1.24
SHELL_MM = 1.2
INFILL = 0.20
SENSOR_MASS_G = 8.5
RATED_TORQUE_NM = 0.1765  # A typical 1.8 kg cm SG90 rating at 4.8 V.
MOVE_RADIANS = math.radians(60)
MOVE_SECONDS = 0.1


def interference(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    """Return the shared volume of two solids in cubic millimetres."""
    if not _bounds_overlap(first, second):
        return 0.0
    with np.errstate(divide="ignore", invalid="ignore"):  # An empty result has zero volume.
        shared = trimesh.boolean.intersection([first, second], engine="manifold")
        return float(abs(shared.volume)) if len(shared.vertices) else 0.0


def _bounds_overlap(first: trimesh.Trimesh, second: trimesh.Trimesh) -> bool:
    return bool(
        np.all(first.bounds[0] <= second.bounds[1]) and np.all(second.bounds[0] <= first.bounds[1])
    )


def lifted(mesh: trimesh.Trimesh, height: float) -> trimesh.Trimesh:
    return mesh.copy().apply_translation([0, 0, height])


def pose(mesh: trimesh.Trimesh, height: float, degrees: float) -> trimesh.Trimesh:
    """Place a cradle-frame part on the servo at a pan angle."""
    rotation = trimesh.transformations.rotation_matrix(math.radians(degrees), [0, 0, 1])
    return lifted(mesh, height).apply_transform(rotation)


def sample_clearance(
    moving: trimesh.Trimesh, fixed: trimesh.Trimesh, points: int = 4000, seed: int = 7
) -> float:
    """Estimate the smallest gap, using vertices and random surface points."""
    samples, _ = trimesh.sample.sample_surface(moving, points, seed=seed)
    query = np.vstack([samples, moving.vertices])
    _, distances, _ = trimesh.proximity.closest_point(fixed, query)
    return float(distances.min())


def sweep(model, angles: range = range(-90, 91, 15)) -> dict:
    """Check every pan angle for collisions and report the tightest gap."""
    meshes = model.meshes
    height = model.info["cradle_z"]
    fixed = trimesh.util.concatenate([meshes["bracket"], meshes["servo"]])
    worst_overlap, worst_gap = 0.0, math.inf
    for angle in angles:
        moving = [pose(meshes["cradle"], height, angle), pose(meshes["sensor"], height, angle)]
        for part in moving:
            worst_overlap = max(
                worst_overlap,
                interference(part, meshes["bracket"]),
                interference(part, meshes["servo"]),
            )
        worst_gap = min(worst_gap, sample_clearance(trimesh.util.concatenate(moving), fixed))
    return {"angles": len(angles), "overlap_mm3": worst_overlap, "min_gap_mm": worst_gap}


def insertion_overlap(part: trimesh.Trimesh, host: trimesh.Trimesh, travel: float) -> float:
    """Slide ``part`` upward out of ``host`` and return the largest overlap on the way."""
    return max(interference(lifted(part, float(z)), host) for z in np.arange(0, travel + 1, 2.0))


def print_mass_g(mesh: trimesh.Trimesh) -> float:
    """Estimate printed mass from solid shells and sparse infill."""
    shell = min(mesh.volume, mesh.area * SHELL_MM)
    solid_equivalent = shell + (mesh.volume - shell) * INFILL
    return solid_equivalent / 1000 * PLA_G_PER_CM3


def rotating_inertia(cradle: trimesh.Trimesh, sensor: trimesh.Trimesh, cradle_g: float) -> float:
    """Return inertia about the pan axis in kg m^2, treating each part as uniform."""
    total = 0.0
    for mesh, grams in ((cradle, cradle_g), (sensor, SENSOR_MASS_G)):
        metres = mesh.copy().apply_scale(1e-3)
        metres.density = (grams / 1000) / metres.volume
        total += float(metres.moment_inertia_frame(np.eye(4))[2, 2])
    return total


def torque_estimate(model) -> dict:
    """Estimate peak torque for a 60 degree move in 0.1 s with a triangular speed profile."""
    cradle_g = print_mass_g(model.meshes["cradle"])
    inertia = rotating_inertia(model.meshes["cradle"], model.meshes["sensor"], cradle_g)
    acceleration = 4 * MOVE_RADIANS / MOVE_SECONDS**2
    torque = inertia * acceleration
    return {
        "inertia_kg_m2": inertia,
        "peak_torque_nm": torque,
        "share_of_rated": torque / RATED_TORQUE_NM,
    }
