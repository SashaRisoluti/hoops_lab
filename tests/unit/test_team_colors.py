"""Contrast lift and collision resolution for team accent colors."""

from __future__ import annotations

import pytest

from dashboard.components.theme import BG_PAGE, TEAM_ACCENTS
from hoops_lab.visuals import team_colors as tc

# Groups of teams whose official accents are byte-identical in TEAM_ACCENTS.
DUPLICATE_GROUPS = [
    ("ATL", "POR"),
    ("CHI", "HOU"),
    ("CHI", "TOR"),
    ("HOU", "TOR"),
    ("CLE", "IND"),
    ("DET", "LAC"),
    ("MIA", "UTA"),
]


# ---- hex <-> hsl ------------------------------------------------------------


def test_pure_red_converts_to_known_hsl() -> None:
    h, s, lightness = tc.hex_to_hsl("#ff0000")
    assert h == pytest.approx(0.0)
    assert s == pytest.approx(1.0)
    assert lightness == pytest.approx(0.5)


def test_black_and_white_sit_at_the_lightness_extremes() -> None:
    assert tc.hex_to_hsl("#000000")[2] == pytest.approx(0.0)
    assert tc.hex_to_hsl("#ffffff")[2] == pytest.approx(1.0)


def test_primary_blue_converts_to_known_hsl() -> None:
    # #0052ff -> rgb(0, 82, 255): max is blue, so hue = 60 * (4 + (r-g)/delta).
    h, s, lightness = tc.hex_to_hsl("#0052ff")
    assert h == pytest.approx(220.7, abs=0.1)
    assert s == pytest.approx(1.0)
    assert lightness == pytest.approx(0.5)


def test_hex_to_hsl_round_trips_exactly_for_every_team_accent() -> None:
    for tricode, value in TEAM_ACCENTS.items():
        h, s, lightness = tc.hex_to_hsl(value)
        assert tc.hsl_to_hex(h, s, lightness) == value.lower(), tricode


def test_hsl_to_hex_returns_lowercase_six_digit_hex() -> None:
    assert tc.hsl_to_hex(0.0, 1.0, 0.5) == "#ff0000"


# ---- contrast ---------------------------------------------------------------


def test_black_on_white_is_the_maximum_contrast_ratio() -> None:
    assert tc.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)


def test_a_colour_against_itself_has_no_contrast() -> None:
    assert tc.contrast_ratio("#5A2D81", "#5A2D81") == pytest.approx(1.0, abs=1e-6)


def test_contrast_is_symmetric() -> None:
    assert tc.contrast_ratio("#007A33", BG_PAGE) == pytest.approx(
        tc.contrast_ratio(BG_PAGE, "#007A33")
    )


# ---- minimal contrast lift --------------------------------------------------


def test_lift_leaves_a_colour_that_already_clears_the_target_untouched() -> None:
    # GSW #FFC72C is one of the brightest accents; it needs no help.
    assert tc.ensure_contrast(TEAM_ACCENTS["GSW"], BG_PAGE) == TEAM_ACCENTS["GSW"].lower()


def test_lift_raises_the_one_accent_that_genuinely_fails() -> None:
    # SAC #5A2D81 is the only accent below 3.0 against the page background.
    lifted = tc.ensure_contrast(TEAM_ACCENTS["SAC"], BG_PAGE, min_ratio=3.0)
    assert tc.contrast_ratio(lifted, BG_PAGE) >= 3.0


def test_lift_stops_as_soon_as_the_target_is_met() -> None:
    lifted = tc.ensure_contrast(TEAM_ACCENTS["SAC"], BG_PAGE, min_ratio=3.0)
    # Overshooting is what turns a franchise colour into neon.
    assert tc.contrast_ratio(lifted, BG_PAGE) < 3.6


def test_lift_preserves_hue() -> None:
    original_hue = tc.hex_to_hsl(TEAM_ACCENTS["SAC"])[0]
    lifted_hue = tc.hex_to_hsl(tc.ensure_contrast(TEAM_ACCENTS["SAC"], BG_PAGE))[0]
    assert lifted_hue == pytest.approx(original_hue, abs=1.5)


def test_lift_preserves_saturation() -> None:
    original_sat = tc.hex_to_hsl(TEAM_ACCENTS["SAC"])[1]
    lifted_sat = tc.hex_to_hsl(tc.ensure_contrast(TEAM_ACCENTS["SAC"], BG_PAGE))[1]
    assert lifted_sat == pytest.approx(original_sat, abs=0.05)


def test_lift_never_darkens_any_team_accent() -> None:
    for tricode, value in TEAM_ACCENTS.items():
        before = tc.hex_to_hsl(value)[2]
        after = tc.hex_to_hsl(tc.ensure_contrast(value, BG_PAGE))[2]
        assert after >= before - 1e-6, tricode


# ---- rgb distance -----------------------------------------------------------


def test_distance_between_identical_colours_is_zero() -> None:
    assert tc.rgb_distance("#CE1141", "#CE1141") == pytest.approx(0.0)


def test_distance_between_black_and_white_is_the_diagonal() -> None:
    assert tc.rgb_distance("#000000", "#ffffff") == pytest.approx(441.67, abs=0.01)


# ---- collision resolution ---------------------------------------------------


@pytest.mark.parametrize(("left", "right"), DUPLICATE_GROUPS)
def test_identical_team_accents_are_separated(left: str, right: str) -> None:
    a, b = tc.resolve_pair(TEAM_ACCENTS[left], TEAM_ACCENTS[right])
    assert tc.rgb_distance(a, b) >= 90.0, f"{left} vs {right} still collide"


@pytest.mark.parametrize(("left", "right"), DUPLICATE_GROUPS)
def test_resolution_leaves_the_first_colour_untouched(left: str, right: str) -> None:
    a, _ = tc.resolve_pair(TEAM_ACCENTS[left], TEAM_ACCENTS[right])
    assert a == TEAM_ACCENTS[left].lower()


def test_resolution_rotates_the_second_hue_in_whole_22_degree_steps() -> None:
    original_hue = tc.hex_to_hsl("#CE1141")[0]
    _, adjusted = tc.resolve_pair("#CE1141", "#CE1141")
    shift = (tc.hex_to_hsl(adjusted)[0] - original_hue) % 360.0
    assert shift > 0.0
    assert min(shift % 22.0, 22.0 - (shift % 22.0)) < 1.5


def test_resolution_rotates_further_when_one_step_is_not_enough() -> None:
    # A single +22 deg step moves #CE1141 only ~52 RGB units — under the threshold —
    # so the resolver must keep stepping until the pair is genuinely separable.
    _, adjusted = tc.resolve_pair("#CE1141", "#CE1141")
    shift = (tc.hex_to_hsl(adjusted)[0] - tc.hex_to_hsl("#CE1141")[0]) % 360.0
    assert shift > 22.0 + 1.5


def test_colours_that_are_already_distinct_are_left_alone() -> None:
    a, b = tc.resolve_pair("#16c47f", "#e0262c")
    assert (a, b) == ("#16c47f", "#e0262c")


def test_near_but_not_identical_hues_are_separated() -> None:
    # CLE #FDBB30 and LAL #FDB927 differ by a couple of RGB steps.
    a, b = tc.resolve_pair(TEAM_ACCENTS["CLE"], TEAM_ACCENTS["LAL"])
    assert tc.rgb_distance(a, b) >= 90.0


# ---- whole-palette resolution ----------------------------------------------


def test_resolved_accents_keeps_every_team() -> None:
    resolved = tc.resolve_accents(TEAM_ACCENTS, BG_PAGE)
    assert set(resolved) == set(TEAM_ACCENTS)


def test_every_resolved_accent_clears_the_contrast_target() -> None:
    resolved = tc.resolve_accents(TEAM_ACCENTS, BG_PAGE)
    failing = {k: v for k, v in resolved.items() if tc.contrast_ratio(v, BG_PAGE) < 3.0}
    assert not failing, f"still unreadable on the page background: {failing}"


def test_resolution_changes_as_few_accents_as_possible() -> None:
    # Franchise colour is identity. Only the accents that actually fail may move.
    resolved = tc.resolve_accents(TEAM_ACCENTS, BG_PAGE)
    changed = {k for k, v in resolved.items() if v != TEAM_ACCENTS[k].lower()}
    expected = {k for k, v in TEAM_ACCENTS.items() if tc.contrast_ratio(v, BG_PAGE) < 3.0}
    assert changed == expected, f"touched accents that were already readable: {changed - expected}"


def test_resolved_accents_are_valid_hex() -> None:
    for tricode, value in tc.resolve_accents(TEAM_ACCENTS, BG_PAGE).items():
        assert len(value) == 7 and value.startswith("#"), tricode
        int(value[1:], 16)


# ---- theme integration ------------------------------------------------------


def test_theme_exposes_readable_accents_for_every_team() -> None:
    from dashboard.components import theme

    assert set(theme.TEAM_ACCENTS_READABLE) == set(theme.TEAM_ACCENTS)


def test_theme_readable_accents_all_clear_the_contrast_target() -> None:
    from dashboard.components import theme

    failing = {
        k: v
        for k, v in theme.TEAM_ACCENTS_READABLE.items()
        if tc.contrast_ratio(v, theme.BG_PAGE) < 3.0
    }
    assert not failing, f"unreadable on the dark shell: {failing}"


def test_the_rail_paints_the_readable_accent_not_the_raw_one() -> None:
    from dashboard.components import team_rail
    from dashboard.components.theme import CONFERENCES, TEAM_ACCENTS_READABLE

    tricodes = CONFERENCES["WEST"] + CONFERENCES["EAST"]
    mapping = {abbr: 1610612700 + i for i, abbr in enumerate(tricodes)}

    # SAC #5A2D81 is the only accent that fails the contrast target unmodified.
    html = team_rail.build_rail_html(mapping, selected="SAC")
    assert TEAM_ACCENTS_READABLE["SAC"] in html
    assert TEAM_ACCENTS["SAC"].lower() not in html.lower()


def test_the_rail_keeps_a_readable_accent_exactly_as_the_franchise_defines_it() -> None:
    from dashboard.components import team_rail
    from dashboard.components.theme import CONFERENCES

    tricodes = CONFERENCES["WEST"] + CONFERENCES["EAST"]
    mapping = {abbr: 1610612700 + i for i, abbr in enumerate(tricodes)}

    html = team_rail.build_rail_html(mapping, selected="BOS")
    assert TEAM_ACCENTS["BOS"].lower() in html.lower()
