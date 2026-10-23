"""Tests for the closest-pass ruler graphic."""
from src.ruler import HAZARD, SAFE, closest_pass_svg, scale_max


def test_scale_is_10_moon_distances_unless_the_pass_is_farther():
    assert scale_max(0.4) == 10
    assert scale_max(10) == 10
    assert scale_max(10.1) == 20
    assert scale_max(63) == 70


def test_svg_shows_earth_moon_and_the_asteroid_label():
    svg = closest_pass_svg("2026 TX", "Oct 20", 4.2)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert ">Earth<" in svg and ">Moon<" in svg and ">10 Moon distances<" in svg
    assert "2026 TX · Oct 20 · 4.2 Moon distances" in svg


def test_far_pass_stretches_the_scale():
    assert ">70 Moon distances<" in closest_pass_svg("Far one", "Oct 1", 63.0)


def test_hazardous_asteroid_uses_the_hazard_color():
    assert HAZARD in closest_pass_svg("A", "Oct 1", 2.0, hazardous=True)
    assert SAFE in closest_pass_svg("A", "Oct 1", 2.0, hazardous=False)


def test_names_are_escaped_so_outside_data_cannot_inject_markup():
    svg = closest_pass_svg("<script>alert(1)</script>", "Oct 1", 2.0)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
