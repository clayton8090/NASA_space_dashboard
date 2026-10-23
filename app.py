"""Phase 4: Streamlit dashboard. Reads only from the database, never from NASA directly."""
import html
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

from src.insights import FLARE_STRENGTH, asteroid_summary, display_name, flare_summary, fmt_date, safe_url
from src.load import connect_readonly, read_db_path
from src.queries import FLARE_ORDER, date_bounds, latest_apod, load_asteroids, load_flares, totals
from src.ruler import closest_pass_svg

TITLE = "Clayton's Astronomical Dashboard"
DESCRIPTION = (
    "Every day, this dashboard collects fresh data from NASA: the Astronomy Picture of the Day, "
    "the asteroids that passed near Earth, and the flares erupting from the Sun. "
    "Choose a time range on the left to explore what happened."
)
ASTEROID_COLOR = "#1D9E75"
FLARE_COLOR = "#D85A30"

# ---------- words shown to visitors (kept in one place so they're easy to edit) ----------
HELP = {
    "preset": "Choose how far back to look. This applies to every section, including solar flares.",
    "custom": "Pick a start and an end date.",
    "hazardous": (
        "Show only asteroids NASA labels 'potentially hazardous': roughly 140 m or larger, with an orbit "
        "that comes within about 7.5 million km of Earth's orbit. The label means worth monitoring, "
        "not a predicted impact."
    ),
    "closer": "Show only asteroids that passed at or closer than this distance. 1 Moon distance is about 384,400 km.",
    "size": "Hide asteroids smaller than this. 140 m is roughly NASA's size threshold for 'potentially hazardous'.",
    "approaches": "How many times an asteroid passed near Earth, after your filters.",
    "hazardous_metric": (
        "How many of those passes were by asteroids NASA labels 'potentially hazardous' (large, with an orbit "
        "near Earth's). Worth monitoring, not a predicted impact."
    ),
    "closest": "The nearest pass after your filters. 1 Moon distance is about 384,400 km, the distance from Earth to the Moon.",
    "flares": "Solar flares are sudden bursts of energy from the Sun. Only the date filter applies to flares.",
}
PRESETS = {"7 days": 7, "30 days": 30, "90 days": 90, "Custom": None}
CLOSER_THAN = {
    "Any distance": None,
    "50 Moon distances": 50,
    "20 Moon distances": 20,
    "10 Moon distances": 10,
    "5 Moon distances": 5,
    "1 Moon distance": 1,
}
MIN_SIZE = {"Any size": None, "10 m": 10, "50 m": 50, "140 m (hazard-size)": 140, "500 m": 500, "1 km": 1000}
DEFAULTS = {"preset": "7 days", "hazardous_only": False, "closer_than": "Any distance", "min_size": "Any size"}
HAZARD_LABELS = {True: "Potentially hazardous", False: "Not flagged"}

# Look and feel: an observatory-logbook style. Serif headings, monospaced "instrument" numbers,
# and color-coded tabs. If Streamlit ever changes how its page is built, these rules simply stop
# matching and the page falls back to the default look; nothing else depends on them.
PAGE_STYLE = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,500;1,6..72,400&display=swap');
h1, h2, h3 {{ font-family: 'Newsreader', Georgia, 'Times New Roman', serif !important; letter-spacing: -0.01em; }}
.lede {{ font-size: 1.12rem; line-height: 1.6; max-width: 46rem; opacity: 0.85; margin: 0.25rem 0 0.75rem; }}
.logline, .plate-label {{ font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 0.8rem; opacity: 0.65; }}
.logline {{ border-top: 1px solid rgba(128,128,128,0.35); border-bottom: 1px solid rgba(128,128,128,0.35);
           padding: 0.4rem 0; margin: 0 0 1.25rem; }}
.plate-label {{ margin: 0; }}
.credit {{ font-family: 'Newsreader', Georgia, serif; font-style: italic; opacity: 0.8; margin: 0 0 0.5rem; }}
[data-testid="stMetric"] {{ border-top: 3px solid {ASTEROID_COLOR}; padding: 0.5rem 0.75rem 0.25rem;
                           background: rgba(128,128,128,0.08); }}
[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"],
[data-testid="column"]:nth-child(4) [data-testid="stMetric"] {{ border-top-color: {FLARE_COLOR}; }}
[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', ui-monospace, monospace !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 12px; }}
.stTabs [data-baseweb="tab-list"] button {{
    flex: 1; padding: 14px 8px; border-radius: 8px; border: 2px solid currentColor;
}}
.stTabs [data-baseweb="tab-list"] button p {{ font-size: 1.15rem; font-weight: 600; color: inherit; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(1) {{ color: {ASTEROID_COLOR}; }}
.stTabs [data-baseweb="tab-list"] button:nth-child(2) {{ color: {FLARE_COLOR}; }}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"]:nth-child(1) {{
    background: {ASTEROID_COLOR}; border-color: {ASTEROID_COLOR}; color: #ffffff;
}}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"]:nth-child(2) {{
    background: {FLARE_COLOR}; border-color: {FLARE_COLOR}; color: #ffffff;
}}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}
</style>
"""


def color_rule(color):
    st.markdown(f'<div style="border-top: 3px solid {color}; margin: 0 0 0.75rem;"></div>', unsafe_allow_html=True)


st.set_page_config(page_title=TITLE, page_icon="🛰️", layout="wide")
st.markdown(PAGE_STYLE, unsafe_allow_html=True)
st.title(TITLE)
st.markdown(f'<p class="lede">{DESCRIPTION}</p>', unsafe_allow_html=True)

conn = connect_readonly(read_db_path())
if conn is None:
    st.warning("No database found yet. Run `make run` (or `python -m src.pipeline`) to create one.")
    st.stop()

low, high = date_bounds(conn)
if low is None:
    st.info("The database is empty. Run `make run` to fetch data.")
    st.stop()

total_asteroids, total_flares = totals(conn)
st.markdown(
    f'<p class="logline">Logged through {fmt_date(high)} · {total_asteroids:,} asteroid passes · '
    f'{total_flares:,} solar flares · updated daily at 06:15 UTC</p>',
    unsafe_allow_html=True,
)


# ---------- filters (remembered between clicks, with a reset button) ----------
def reset_filters():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state["custom_range"] = (low, high)


for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
saved_range = st.session_state.get("custom_range")
if saved_range is None or any(d < low or d > high for d in saved_range):
    st.session_state["custom_range"] = (low, high)

with st.sidebar:
    st.header("Filters")
    st.markdown("**Dates** (all sections)")
    preset = st.radio("Show the last", list(PRESETS), key="preset", horizontal=True, help=HELP["preset"])
    if preset == "Custom":
        picked = st.date_input(
            "Custom range", key="custom_range", min_value=low, max_value=high, help=HELP["custom"]
        )
    else:
        picked = (max(low, high - timedelta(days=PRESETS[preset] - 1)), high)

    st.divider()
    st.markdown("**Asteroids only**")
    hazardous_only = st.toggle("Potentially hazardous only", key="hazardous_only", help=HELP["hazardous"])
    closer_label = st.select_slider("Closer than", options=list(CLOSER_THAN), key="closer_than", help=HELP["closer"])
    size_label = st.select_slider("Minimum size", options=list(MIN_SIZE), key="min_size", help=HELP["size"])

    st.divider()
    st.button("Reset filters", on_click=reset_filters)
    st.caption(f"Data from {fmt_date(low)} to {fmt_date(high)}")

if not isinstance(picked, (tuple, list)) or len(picked) != 2:
    st.info("Pick an end date in the sidebar to apply the custom range.")
    st.stop()
start, end = picked

asteroids = load_asteroids(
    conn, start, end, hazardous_only,
    max_lunar=CLOSER_THAN[closer_label], min_size_m=MIN_SIZE[size_label],
)
flares = load_flares(conn, start, end)

# ---------- picture of the day: the first thing visitors see, framed like an observatory plate ----------
apod = latest_apod(conn)
if not apod:
    st.info("No picture of the day has been collected yet.")
else:
    with st.container(border=True):
        left, right = st.columns([3, 2])
        with left:
            if apod.get("media_type") == "image" and safe_url(apod.get("image_url")):
                st.image(apod["image_url"])
            elif safe_url(apod.get("page_url")):
                st.markdown(f"Today's feature isn't a still image. [View it on NASA's site]({apod['page_url']})")
        with right:
            if apod.get("apod_date"):
                st.markdown(f'<p class="plate-label">Plate · {fmt_date(apod["apod_date"])}</p>', unsafe_allow_html=True)
            st.subheader(apod.get("title") or "Untitled")
            if apod.get("credit"):
                # Credit text and link come from outside data, so they are escaped before going into HTML.
                name = html.escape(apod["credit"])
                link = safe_url(apod.get("credit_url"))
                credit = f'<a href="{html.escape(link, quote=True)}">{name}</a>' if link else name
                st.markdown(f'<p class="credit">Credit: {credit}</p>', unsafe_allow_html=True)
            if apod.get("explanation"):
                st.write(apod["explanation"])
            if safe_url(apod.get("page_url")):
                st.markdown(f"[View on NASA's site]({apod['page_url']})")
    st.caption("Astronomy Picture of the Day, chosen and explained by professional astronomers.")

# ---------- guide, always visible ----------
with st.container(border=True):
    st.markdown("**How to read this dashboard**")
    g1, g2 = st.columns(2)
    g1.markdown(
        "**Moon distances.** 1 means an asteroid passed as far away as the Moon (about 384,400 km).\n\n"
        "**Solar flare classes.** A, B, C, M, X. Each step is about 10 times stronger than the one before. "
        "M and X flares can cause radio blackouts on Earth."
    )
    g2.markdown(
        "**Potentially hazardous.** NASA's label for asteroids roughly 140 m or larger whose orbits come within "
        "about 7.5 million km of Earth's orbit. Worth monitoring, not a predicted impact.\n\n"
        "**Tips.** Dates apply to every section; the other filters apply to asteroids. "
        "Hover over the ? marks and chart points for details."
    )

# ---------- key numbers ----------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Asteroid approaches", len(asteroids), help=HELP["approaches"])
m2.metric("Potentially hazardous", int(asteroids["is_hazardous"].sum()), help=HELP["hazardous_metric"])
m3.metric(
    "Closest pass (Moon distances)",
    f"{asteroids['miss_distance_lunar'].min():.1f}" if not asteroids.empty else "n/a",
    help=HELP["closest"],
)
m4.metric("Solar flares", len(flares), help=HELP["flares"])

if not asteroids.empty:
    closest = asteroids.loc[asteroids["miss_distance_lunar"].idxmin()]
    st.caption("Closest pass in this range")
    st.markdown(
        closest_pass_svg(
            display_name(closest["name"]),
            fmt_date(closest["approach_date"], with_year=False),
            float(closest["miss_distance_lunar"]),
            hazardous=bool(closest["is_hazardous"]),
        ),
        unsafe_allow_html=True,
    )

tab_asteroids, tab_flares = st.tabs(["Asteroids", "Solar flares"])

# ---------- asteroids ----------
with tab_asteroids:
    color_rule(ASTEROID_COLOR)
    st.caption(
        "Each dot is one asteroid passing Earth. Farther right means it passed farther away; "
        "higher means it is bigger. Hover over a dot for details."
    )
    st.write(asteroid_summary(asteroids, start, end))
    if not asteroids.empty:
        data = asteroids.assign(
            asteroid=asteroids["name"].map(display_name),
            size_m=(asteroids["diameter_min_m"] + asteroids["diameter_max_m"]) / 2,
            status=asteroids["is_hazardous"].map(HAZARD_LABELS),
        )
        chart = (
            alt.Chart(data)
            .mark_circle(size=90, opacity=0.8)
            .encode(
                x=alt.X(
                    "miss_distance_lunar:Q",
                    scale=alt.Scale(type="log"),
                    title="Miss distance (Moon distances, log scale)",
                ),
                y=alt.Y("size_m:Q", scale=alt.Scale(type="log"), title="Estimated size (meters, log scale)"),
                color=alt.Color(
                    "status:N",
                    title=None,
                    scale=alt.Scale(domain=list(HAZARD_LABELS.values()), range=["#e45756", "#4c78a8"]),
                    legend=alt.Legend(orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("asteroid:N", title="Asteroid"),
                    alt.Tooltip("approach_date:N", title="Date"),
                    alt.Tooltip("size_m:Q", title="Estimated size (m)", format=",.0f"),
                    alt.Tooltip("velocity_kps:Q", title="Speed (km/s)", format=".1f"),
                    alt.Tooltip("miss_distance_lunar:Q", title="Miss distance (Moon distances)", format=".1f"),
                    alt.Tooltip("miss_distance_km:Q", title="Miss distance (km)", format=",.0f"),
                    alt.Tooltip("status:N", title="NASA label"),
                ],
            )
            .properties(height=380, width="container")
        )
        st.altair_chart(chart)
        st.markdown("**All approaches**")
        st.dataframe(
            data[["approach_date", "asteroid", "size_m", "velocity_kps", "miss_distance_lunar", "status"]],
            hide_index=True,
            height=300,
            column_config={
                "approach_date": "Date",
                "asteroid": "Asteroid",
                "size_m": st.column_config.NumberColumn("Estimated size (m)", format="%.0f"),
                "velocity_kps": st.column_config.NumberColumn("Speed (km/s)", format="%.1f"),
                "miss_distance_lunar": st.column_config.NumberColumn("Miss distance (Moon distances)", format="%.1f"),
                "status": "NASA label",
            },
        )

# ---------- solar flares ----------
with tab_flares:
    color_rule(FLARE_COLOR)
    st.caption(
        "Solar flares are sudden bursts of energy from the Sun. Classes run A, B, C, M, X, "
        "and each step is about 10 times stronger than the one before."
    )
    st.write(flare_summary(flares))
    if not flares.empty:
        counts = (
            flares["class_letter"].value_counts()
            .reindex(FLARE_ORDER, fill_value=0)
            .rename_axis("flare_class")
            .reset_index(name="flares")
        )
        counts["strength"] = counts["flare_class"].map(FLARE_STRENGTH)
        bars = (
            alt.Chart(counts)
            .mark_bar(color=FLARE_COLOR)
            .encode(
                x=alt.X("flare_class:N", sort=FLARE_ORDER, title="Flare class (weakest to strongest)"),
                y=alt.Y("flares:Q", title="Number of flares", axis=alt.Axis(tickMinStep=1, format="d")),
                tooltip=[
                    alt.Tooltip("flare_class:N", title="Class"),
                    alt.Tooltip("strength:N", title="Strength"),
                    alt.Tooltip("flares:Q", title="Flares"),
                ],
            )
            .properties(height=300, width="container")
        )
        st.altair_chart(bars)
        st.markdown("**All flares**")
        table = flares.assign(
            started=pd.to_datetime(flares["begin_time"], utc=True).dt.strftime("%b %d, %Y %H:%M UTC"),
            strength=flares["class_letter"].map(FLARE_STRENGTH),
        )
        st.dataframe(
            table[["started", "class_type", "strength", "duration_min", "source_location"]],
            hide_index=True,
            height=300,
            column_config={
                "started": "Started",
                "class_type": "Class",
                "strength": "Strength",
                "duration_min": st.column_config.NumberColumn("Duration (minutes)", format="%.0f"),
                "source_location": "Location on the Sun",
            },
        )

st.divider()
st.caption(
    "Data: NASA Open APIs (NeoWs, APOD). Space weather from DONKI, courtesy of the "
    "NASA Community Coordinated Modeling Center (CCMC). This project is not endorsed by NASA."
)
