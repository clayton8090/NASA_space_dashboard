"""Plain-language summaries for the dashboard. Pure functions with no Streamlit, so they're easy to test."""
from datetime import date

FLARE_ORDER = ["A", "B", "C", "M", "X"]  # weakest to strongest; each step about 10x stronger
FLARE_STRENGTH = {"A": "minor", "B": "minor", "C": "small", "M": "moderate", "X": "strong"}


def fmt_date(value, with_year=True):
    """'2026-10-23' or a date -> 'Oct 23, 2026' (or 'Oct 23' without the year)."""
    d = date.fromisoformat(str(value)[:10])
    return f"{d:%b} {d.day}, {d.year}" if with_year else f"{d:%b} {d.day}"


def display_name(name):
    """NeoWs wraps provisional names in parentheses, like '(2020 AA)'. Drop them for display."""
    name = str(name)
    if name.startswith("(") and name.endswith(")") and name.count("(") == 1:
        return name[1:-1]
    return name


def asteroid_summary(df, start, end):
    """One or two sentences describing the asteroid data currently shown."""
    period = f"between {fmt_date(start, with_year=False)} and {fmt_date(end)}"
    if df.empty:
        return f"No asteroid close approaches match your filters {period}."
    n = len(df)
    closest = df.loc[df["miss_distance_lunar"].idxmin()]
    text = (
        f"{n} asteroid close approach{'es' if n != 1 else ''} {period}. "
        f"The closest was {display_name(closest['name'])}, which passed "
        f"{closest['miss_distance_lunar']:.1f} times the Earth-Moon distance away "
        f"on {fmt_date(closest['approach_date'], with_year=False)}."
    )
    hazardous = int(df["is_hazardous"].sum())
    if hazardous:
        text += (
            f" {hazardous} {'is' if hazardous == 1 else 'are'} labeled potentially hazardous, "
            "which means worth monitoring, not a predicted impact."
        )
    return text


def strongest_flare(df):
    """The row of the strongest flare (by class letter, then number), or None."""
    ranked = df.dropna(subset=["class_letter"])
    ranked = ranked[ranked["class_letter"].isin(FLARE_ORDER)]
    if ranked.empty:
        return None
    ranked = ranked.assign(rank=ranked["class_letter"].map(FLARE_ORDER.index))
    return ranked.sort_values(["rank", "class_magnitude"]).iloc[-1]


def flare_summary(df):
    """One or two sentences describing the solar flare data currently shown."""
    if df.empty:
        return "No solar flares match your filters in this date range."
    n = len(df)
    text = f"{n} solar flare{'s' if n != 1 else ''} in this date range."
    top = strongest_flare(df)
    if top is not None:
        text += (
            f" The strongest was {top['class_type']} "
            f"({FLARE_STRENGTH[top['class_letter']]}) on {fmt_date(top['begin_time'], with_year=False)}."
        )
    big = int(df["class_letter"].isin(["M", "X"]).sum())
    if big:
        text += f" {big} reached M or X class, the levels that can cause radio blackouts."
    else:
        text += " None reached M or X class, the levels that can cause radio blackouts."
    return text
