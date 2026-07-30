"""Readable team accent colors on a dark surface.

A franchise color is identity, so the guiding rule here is to change as little as
possible. Two pure transforms, each applied only when a measurement says it is needed:

* :func:`ensure_contrast` raises lightness just far enough to clear a WCAG contrast
  ratio against the surface the color is painted on, leaving hue and saturation alone.
  Measured against this project's near-black page background only one of the thirty
  official accents actually fails, so twenty-nine are passed through untouched. A fixed
  lightness floor was tried first and rejected: it "fixed" eighteen colors that were
  already legible and turned them neon.
* :func:`resolve_pair` separates two colors a viewer could not tell apart, by rotating
  the second one's hue in 22 degree steps until they are distinguishable. Five groups
  of franchises share a byte-identical hex, so any head-to-head surface needs this.
"""

from __future__ import annotations

import colorsys
from collections.abc import Mapping

#: WCAG 2.1 minimum contrast for graphical objects and large text.
MIN_CONTRAST = 3.0

#: Euclidean RGB distance below which two colors are treated as the same.
MIN_DISTANCE = 90.0

#: Hue rotation applied to the second color of a colliding pair, in degrees.
HUE_STEP = 22.0

#: Near-hue pairs are also separated when they are this close in RGB space.
NEAR_HUE_DEGREES = 35.0
NEAR_HUE_DISTANCE = 160.0

_MAX_STEPS = 8


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Return the 0-255 RGB channels of a ``#rrggbb`` string."""
    raw = value.lstrip("#")
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def hex_to_hsl(value: str) -> tuple[float, float, float]:
    """Return ``(hue in degrees, saturation, lightness)`` for a ``#rrggbb`` string."""
    r, g, b = (channel / 255 for channel in hex_to_rgb(value))
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return hue * 360.0, saturation, lightness


def hsl_to_hex(hue: float, saturation: float, lightness: float) -> str:
    """Return the lowercase ``#rrggbb`` string for an HSL triple."""
    r, g, b = colorsys.hls_to_rgb((hue % 360.0) / 360.0, lightness, saturation)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def rgb_distance(left: str, right: str) -> float:
    """Return the Euclidean distance between two colors in RGB space."""
    a = hex_to_rgb(left)
    b = hex_to_rgb(right)
    return sum((x - y) ** 2 for x, y in zip(a, b, strict=True)) ** 0.5


def hue_delta(left: str, right: str) -> float:
    """Return the smaller of the two arcs between the hues, in degrees."""
    raw = abs(hex_to_hsl(left)[0] - hex_to_hsl(right)[0]) % 360.0
    return min(raw, 360.0 - raw)


def relative_luminance(value: str) -> float:
    """Return the WCAG relative luminance of a ``#rrggbb`` string."""

    def channel(raw: int) -> float:
        c = raw / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(x) for x in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(left: str, right: str) -> float:
    """Return the WCAG contrast ratio between two colors, from 1.0 to 21.0."""
    a, b = sorted((relative_luminance(left), relative_luminance(right)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def ensure_contrast(
    value: str, background: str, min_ratio: float = MIN_CONTRAST, step: float = 0.01
) -> str:
    """Lighten ``value`` the least amount that clears ``min_ratio`` against ``background``.

    Returns the color unchanged when it already passes, which is the common case: the
    point is to rescue the few accents that genuinely fail, not to normalise all of them.
    """
    if contrast_ratio(value, background) >= min_ratio:
        return value.lower()

    hue, saturation, lightness = hex_to_hsl(value)
    while lightness < 1.0:
        lightness = min(1.0, lightness + step)
        candidate = hsl_to_hex(hue, saturation, lightness)
        if contrast_ratio(candidate, background) >= min_ratio:
            return candidate
    return "#ffffff"


def collides(left: str, right: str) -> bool:
    """Report whether a viewer would struggle to tell the two colors apart."""
    distance = rgb_distance(left, right)
    if distance < MIN_DISTANCE:
        return True
    return hue_delta(left, right) < NEAR_HUE_DEGREES and distance < NEAR_HUE_DISTANCE


def resolve_pair(left: str, right: str) -> tuple[str, str]:
    """Return the pair with ``right`` rotated away from ``left`` if they collide.

    ``left`` is never modified, so the first team of a matchup keeps its real color.
    Rotation stops as soon as the two are distinguishable; a single step is not always
    enough, because a small hue change near the red end of the wheel barely moves the
    color in RGB space.
    """
    a = left.lower()
    b = right.lower()
    if not collides(a, b):
        return a, b

    hue, saturation, lightness = hex_to_hsl(b)
    for step in range(1, _MAX_STEPS + 1):
        candidate = hsl_to_hex(hue + HUE_STEP * step, saturation, lightness)
        if not collides(a, candidate):
            return a, candidate
    return a, hsl_to_hex(hue + HUE_STEP * _MAX_STEPS, saturation, lightness)


def resolve_accents(
    accents: Mapping[str, str], background: str, min_ratio: float = MIN_CONTRAST
) -> dict[str, str]:
    """Return every accent guaranteed readable against ``background``.

    Accents that already pass come back untouched, so franchise identity survives.
    Collisions stay unresolved here on purpose: rewriting all 30 to be mutually
    distinct would distort colors that are only ever shown alone. Pairwise separation
    is applied by :func:`resolve_pair` where two teams actually appear together.
    """
    return {
        tricode: ensure_contrast(value, background, min_ratio) for tricode, value in accents.items()
    }
