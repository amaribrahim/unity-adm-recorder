"""Tests for coordinates.py — Unity world-space to ADM Cartesian conversion."""

import pytest

from adm_encoder.coordinates import unity_to_adm

R = 20.0  # scene radius used throughout


@pytest.mark.parametrize(
    "unity_xyz, expected_adm",
    [
        ((R, 0, 0),   (1.0,  0.0,  0.0)),   # hard right
        ((-R, 0, 0),  (-1.0, 0.0,  0.0)),   # hard left
        ((0, 0, R),   (0.0,  1.0,  0.0)),   # front
        ((0, 0, -R),  (0.0, -1.0,  0.0)),   # rear
        ((0, R, 0),   (0.0,  0.0,  1.0)),   # overhead
        ((0, -R, 0),  (0.0,  0.0, -1.0)),   # floor
        ((0, 0, 0),   (0.0,  0.0,  0.0)),   # center
    ],
)
def test_cardinal_positions(
    unity_xyz: tuple[float, float, float],
    expected_adm: tuple[float, float, float],
) -> None:
    result = unity_to_adm(*unity_xyz, scene_radius=R)
    assert result == pytest.approx(expected_adm, abs=1e-9)


def test_scaling() -> None:
    adm_x, adm_y, adm_z = unity_to_adm(10.0, 0.0, 0.0, scene_radius=20.0)
    assert adm_x == pytest.approx(0.5)
    assert adm_y == pytest.approx(0.0)
    assert adm_z == pytest.approx(0.0)


def test_clamp_above() -> None:
    adm_x, _, _ = unity_to_adm(999.0, 0.0, 0.0, scene_radius=20.0)
    assert adm_x == 1.0


def test_clamp_below() -> None:
    adm_x, _, _ = unity_to_adm(-999.0, 0.0, 0.0, scene_radius=20.0)
    assert adm_x == -1.0


def test_diagonal() -> None:
    r = 20.0
    adm_x, adm_y, adm_z = unity_to_adm(r * 0.5, r * 0.5, r * 0.5, scene_radius=r)
    assert adm_x == pytest.approx(0.5)
    assert adm_y == pytest.approx(0.5)   # Unity Z → ADM Y
    assert adm_z == pytest.approx(0.5)   # Unity Y → ADM Z


def test_axis_remap_z_maps_to_adm_y() -> None:
    _, adm_y, _ = unity_to_adm(0.0, 0.0, 10.0, scene_radius=20.0)
    assert adm_y == pytest.approx(0.5)


def test_axis_remap_y_maps_to_adm_z() -> None:
    _, _, adm_z = unity_to_adm(0.0, 10.0, 0.0, scene_radius=20.0)
    assert adm_z == pytest.approx(0.5)
