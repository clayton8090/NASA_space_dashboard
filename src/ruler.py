"""The 'closest pass' ruler: Earth at 0, the Moon at 1, and the closest asteroid at its real distance.

Builds a small SVG as text. Pure Python with no Streamlit, so it's easy to test.
"""
import html
import math

WIDTH, LEFT, RIGHT, LINE_Y = 640, 24, 616, 40
MUTED = "#9aa0a6"          # readable on both dark and light backgrounds
EARTH = "#378ADD"
SAFE, HAZARD = "#4c78a8", "#e45756"   # same colors as the asteroid chart


def scale_max(lunar):
    """10 Moon distances, or the next multiple of 10 if the closest pass is farther than that."""
    return 10 if lunar <= 10 else int(math.ceil(lunar / 10.0)) * 10


def _x(value, top):
    return LEFT + (RIGHT - LEFT) * (value / top)


def closest_pass_svg(name, date_label, lunar, hazardous=False):
    top = scale_max(lunar)
    ax, moon_x = _x(lunar, top), _x(1, top)
    anchor = "start" if ax < LEFT + 120 else ("end" if ax > RIGHT - 120 else "middle")
    label = html.escape(f"{name} · {date_label} · {lunar:.1f} Moon distances")
    color = HAZARD if hazardous else SAFE
    return (
        f'<svg viewBox="0 0 {WIDTH} 76" width="100%" role="img" '
        f'aria-label="Closest pass: {label}" style="max-width:{WIDTH}px;display:block">'
        f'<line x1="{LEFT}" y1="{LINE_Y}" x2="{RIGHT}" y2="{LINE_Y}" stroke="{MUTED}" stroke-width="1"/>'
        f'<line x1="{RIGHT}" y1="{LINE_Y - 5}" x2="{RIGHT}" y2="{LINE_Y + 5}" stroke="{MUTED}"/>'
        f'<circle cx="{LEFT}" cy="{LINE_Y}" r="7" fill="{EARTH}"/>'
        f'<circle cx="{moon_x:.1f}" cy="{LINE_Y}" r="4" fill="{MUTED}"/>'
        f'<circle cx="{ax:.1f}" cy="{LINE_Y}" r="6" fill="{color}"/>'
        f'<g font-family="IBM Plex Mono, ui-monospace, monospace" font-size="12" fill="{MUTED}">'
        f'<text x="{LEFT}" y="{LINE_Y + 24}" text-anchor="middle">Earth</text>'
        f'<text x="{moon_x:.1f}" y="{LINE_Y + 24}" text-anchor="{"start" if moon_x - LEFT < 40 else "middle"}">Moon</text>'
        f'<text x="{RIGHT}" y="{LINE_Y + 24}" text-anchor="end">{top} Moon distances</text>'
        f'<text x="{ax:.1f}" y="{LINE_Y - 14}" text-anchor="{anchor}" fill="{color}">{label}</text>'
        f'</g></svg>'
    )
