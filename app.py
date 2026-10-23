"""Phase 4: Streamlit dashboard. Reads only from the database, never from NASA directly."""
from datetime import date

import streamlit as st

from src.load import connect_readonly, read_db_path
from src.queries import FLARE_ORDER, date_bounds, latest_apod, load_asteroids, load_flares

st.set_page_config(page_title="NASA Space Dashboard", page_icon="🛰️", layout="wide")
st.title("NASA Space Dashboard")
st.caption("Near-Earth asteroids, solar flares, and the Astronomy Picture of the Day")

conn = connect_readonly(read_db_path())
if conn is None:
    st.warning("No database found yet. Run `make run` (or `python -m src.pipeline`) to create one.")
    st.stop()

low, high = date_bounds(conn)
if low is None:
    st.info("The database is empty. Run `make run` to fetch data.")
    st.stop()

# ---------- sidebar filters ----------
st.sidebar.header("Filters")
picked = st.sidebar.date_input("Date range", value=(low, high), min_value=low, max_value=high)
if isinstance(picked, (tuple, list)):
    if len(picked) != 2:
        st.sidebar.info("Pick an end date to apply the range.")
        st.stop()
    start, end = picked
else:
    start = end = picked
hazardous_only = st.sidebar.toggle("Potentially hazardous asteroids only")
min_class = st.sidebar.select_slider("Minimum flare class", options=FLARE_ORDER, value="A")

# ---------- picture of the day ----------
apod = latest_apod(conn)
if apod:
    st.header("Astronomy Picture of the Day")
    left, right = st.columns([2, 3])
    with left:
        if apod.get("media_type") == "image" and apod.get("image_url"):
            st.image(apod["image_url"])
        elif apod.get("page_url"):
            st.markdown(f"[Open today's feature]({apod['page_url']})")
    with right:
        st.subheader(apod.get("title") or "Untitled")
        st.caption(apod.get("apod_date") or "")
        st.write(apod.get("explanation") or "")
        credit = apod.get("credit")
        if credit:
            credit_url = apod.get("credit_url")
            st.caption(f"Credit: [{credit}]({credit_url})" if credit_url else f"Credit: {credit}")

# ---------- asteroids ----------
st.header("Near-Earth asteroids")
asteroids = load_asteroids(conn, start, end, hazardous_only)
c1, c2, c3 = st.columns(3)
c1.metric("Approaches", len(asteroids))
c2.metric("Potentially hazardous", int(asteroids["is_hazardous"].sum()))
c3.metric(
    "Closest pass (lunar distances)",
    f"{asteroids['miss_distance_lunar'].min():.1f}" if not asteroids.empty else "n/a",
)

if asteroids.empty:
    st.info("No asteroid approaches match these filters.")
else:
    chart_df = asteroids.assign(
        avg_diameter_m=(asteroids["diameter_min_m"] + asteroids["diameter_max_m"]) / 2,
        status=asteroids["is_hazardous"].map({True: "Potentially hazardous", False: "Not flagged"}),
    )
    st.subheader("Size vs. miss distance")
    st.scatter_chart(
        chart_df,
        x="miss_distance_lunar",
        y="avg_diameter_m",
        color="status",
        size="velocity_kps",
    )
    st.subheader("Approaches per day")
    st.bar_chart(asteroids.groupby("approach_date").size())
    st.dataframe(
        asteroids[[
            "approach_date", "name", "diameter_min_m", "diameter_max_m",
            "velocity_kps", "miss_distance_lunar", "is_hazardous",
        ]],
        hide_index=True,
    )

# ---------- solar flares ----------
st.header("Solar flares")
flares = load_flares(conn, start, end, min_class)
f1, f2 = st.columns(2)
f1.metric("Flares", len(flares))
if flares.empty:
    f2.metric("Strongest", "n/a")
    st.info("No solar flares match these filters.")
else:
    ranked = flares.dropna(subset=["class_letter"]).copy()
    ranked["rank"] = ranked["class_letter"].map(FLARE_ORDER.index)
    strongest = ranked.sort_values(["rank", "class_magnitude"]).iloc[-1] if not ranked.empty else None
    f2.metric("Strongest", strongest["class_type"] if strongest is not None else "n/a")
    st.subheader("Flares by class")
    st.bar_chart(flares["class_letter"].value_counts().reindex(FLARE_ORDER, fill_value=0))
    st.dataframe(
        flares[["begin_time", "class_type", "duration_min", "source_location", "active_region"]],
        hide_index=True,
    )

st.divider()
st.caption(
    "Data: NASA Open APIs (NeoWs, APOD). Space weather from DONKI, courtesy of the "
    "NASA Community Coordinated Modeling Center (CCMC). "
    f"This project is not endorsed by NASA. Page rendered {date.today().isoformat()}."
)
