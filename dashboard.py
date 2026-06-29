"""
ParkVision — Streamlit Dashboard
==================================
Real-time analytics dashboard that reads from the SQLite database
written by the processing pipeline.

Launch
------
    streamlit run dashboard.py
  or with a custom DB path:
    streamlit run dashboard.py -- --db /path/to/parkvision.db

Features
--------
  • Metric cards   — Total / Occupied / Available slot counts
  • Live table     — Per-slot status + last-updated timestamp
  • Session log    — Recent completed parking sessions with duration
  • Peak hours     — Bar chart of busiest hours of the day
  • Occupancy rate — Gauge / line chart

Author : ParkVision
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="ParkVision Dashboard",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for dark theme polish ─────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Top-bar ── */
    header[data-testid="stHeader"] { background: #0d0d0d; }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: #1a1a2e;
        border: 1px solid #2a2a4e;
        border-radius: 10px;
        padding: 16px 20px;
    }
    div[data-testid="metric-container"] label {
        color: #9ea3b0 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }

    /* ── Section headers ── */
    h2, h3 { color: #e0e0ff; }

    /* ── Dataframe ── */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] { background: #111122; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Argument parsing (Streamlit passes custom args after "--") ────────────────
def _get_db_path() -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", default="parkvision.db")
    # sys.argv[0] is the script path; Streamlit may insert its own args
    # before "--", so we parse only what comes after it.
    try:
        sep = sys.argv.index("--")
        custom_args = sys.argv[sep + 1:]
    except ValueError:
        custom_args = []
    args, _ = parser.parse_known_args(custom_args)
    return Path(args.db)


DB_PATH = _get_db_path()


# ── DB helpers ────────────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        st.error(
            f"Database not found: **{DB_PATH}**  \n"
            "Run `python main.py <video>` first to generate the database.",
            icon="🚫",
        )
        st.stop()
    return sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=5)


@st.cache_data(ttl=3)   # refresh every 3 seconds
def _load_slot_status() -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql_query(
        "SELECT slot_id, status, last_updated FROM slot_status ORDER BY slot_id",
        conn,
    )
    conn.close()
    return df


@st.cache_data(ttl=3)
def _load_recent_logs(limit: int = 300) -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT slot_id,
               entry_time,
               exit_time,
               ROUND(total_duration / 60.0, 2) AS duration_min
        FROM parking_logs
        WHERE exit_time IS NOT NULL
        ORDER BY exit_time DESC
        LIMIT ?
        """,
        conn,
        params=(limit,),
    )
    conn.close()
    return df


@st.cache_data(ttl=10)
def _load_hourly_stats() -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT CAST(SUBSTR(entry_time, 12, 2) AS INTEGER) AS hour,
               COUNT(*) AS sessions
        FROM parking_logs
        WHERE entry_time IS NOT NULL
        GROUP BY hour
        ORDER BY hour
        """,
        conn,
    )
    conn.close()
    # Fill any missing hours with 0
    all_hours = pd.DataFrame({"hour": list(range(24))})
    df = all_hours.merge(df, on="hour", how="left").fillna(0)
    df["sessions"] = df["sessions"].astype(int)
    return df


@st.cache_data(ttl=3)
def _load_occupancy_timeline() -> pd.DataFrame:
    """Build an occupancy timeline from parking_logs."""
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT entry_time AS ts, 1 AS delta
        FROM parking_logs WHERE entry_time IS NOT NULL
        UNION ALL
        SELECT exit_time AS ts, -1 AS delta
        FROM parking_logs WHERE exit_time IS NOT NULL
        ORDER BY ts
        """,
        conn,
    )
    conn.close()
    if df.empty:
        return df
    df["ts"]         = pd.to_datetime(df["ts"])
    df["occupancy"]  = df["delta"].cumsum()
    return df[["ts", "occupancy"]]


# ── Layout ────────────────────────────────────────────────────────────────────
def render() -> None:
    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/parking.png",
            width=80,
        )
        st.title("ParkVision")
        st.caption("Aerial Parking Management System")
        st.divider()
        st.markdown(f"**Database:** `{DB_PATH.name}`")
        refresh = st.slider("Auto-refresh (sec)", 2, 30, 5)
        st.divider()
        st.markdown(
            "🟢 Occupied &nbsp;&nbsp; 🔴 Free",
            unsafe_allow_html=True,
        )
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("## 🅿️ &nbsp; ParkVision — Live Parking Dashboard")

    slot_df  = _load_slot_status()
    log_df   = _load_recent_logs()
    hour_df  = _load_hourly_stats()
    occ_df   = _load_occupancy_timeline()

    total    = len(slot_df)
    occupied = int((slot_df["status"] == "Occupied").sum())
    free     = total - occupied
    occ_rate = (occupied / total * 100) if total else 0.0

    # ── Metric cards ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🅿️ Total Slots",    total)
    c2.metric("🟢 Occupied",       occupied,
              delta=f"{occ_rate:.1f}% occupancy",
              delta_color="off")
    c3.metric("🔴 Available",       free)
    c4.metric("⏱️ Avg Session (min)",
              f"{log_df['duration_min'].mean():.1f}" if not log_df.empty else "—")

    st.divider()

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([1.4, 1], gap="large")

    with left:
        st.markdown("### 📋 Current Slot Status")

        # Colour-code status column
        def _colour_status(val: str) -> str:
            if val == "Occupied":
                return "background-color:#1b4332; color:#52b788;"
            return "background-color:#3d0000; color:#ff6b6b;"

        styled = slot_df.style.applymap(
            _colour_status, subset=["status"]
        ).format({"slot_id": "{:d}"})

        st.dataframe(styled, use_container_width=True, height=420)

    with right:
        st.markdown("### ⏱️ Recent Sessions")
        if log_df.empty:
            st.info("No completed sessions yet.", icon="ℹ️")
        else:
            st.dataframe(
                log_df.rename(columns={
                    "slot_id":      "Slot",
                    "entry_time":   "Entry",
                    "exit_time":    "Exit",
                    "duration_min": "Duration (min)",
                }),
                use_container_width=True,
                height=420,
            )

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2, gap="large")

    with ch1:
        st.markdown("### 📊 Peak Hours")
        if hour_df.empty or hour_df["sessions"].sum() == 0:
            st.info("No session data yet.")
        else:
            st.bar_chart(
                hour_df.set_index("hour")["sessions"],
                use_container_width=True,
                height=280,
                color="#4cc9f0",
            )

    with ch2:
        st.markdown("### 📈 Occupancy Over Time")
        if occ_df.empty:
            st.info("No occupancy timeline yet.")
        else:
            st.line_chart(
                occ_df.set_index("ts")["occupancy"],
                use_container_width=True,
                height=280,
                color="#f72585",
            )

    st.divider()

    # ── Occupancy gauge (progress bar) ────────────────────────────────────────
    st.markdown("### 🎯 Current Occupancy Rate")
    bar_colour = (
        "🟥" if occ_rate >= 80
        else "🟧" if occ_rate >= 50
        else "🟩"
    )
    st.markdown(
        f"**{bar_colour}  {occ_rate:.1f} %**  of {total} slots occupied"
    )
    st.progress(min(occ_rate / 100, 1.0))

    # ── Auto-refresh ─────────────────────────────────────────────────────────
    time.sleep(refresh)
    st.rerun()


if __name__ == "__main__":
    render()
