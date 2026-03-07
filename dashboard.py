import sqlite3
import time

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = "trading.db"

st.set_page_config(page_title="Trading Bot", layout="wide")
st.title("Trading Bot Dashboard")


def load(query: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


# ── Portfolio metrics ─────────────────────────────────────────────────────────
snaps = load("SELECT * FROM portfolio_snapshots ORDER BY timestamp")

if not snaps.empty:
    latest = snaps.iloc[-1]
    first = snaps.iloc[0]
    pnl = latest.equity - first.equity
    pnl_pct = (pnl / first.equity) * 100 if first.equity else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Equity", f"${latest.equity:,.2f}", f"{pnl_pct:+.2f}% all-time")
    c2.metric("Cash", f"${latest.cash:,.2f}")
    c3.metric("Open Positions", int(latest.position_count))
    c4.metric("Snapshots", len(snaps))

    # ── Equity curve ─────────────────────────────────────────────────────────
    st.subheader("Equity Curve")
    fig = px.line(
        snaps,
        x="timestamp",
        y="equity",
        markers=True,
        labels={"timestamp": "Time (UTC)", "equity": "Equity ($)"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No portfolio snapshots yet — run the bot first.")

st.divider()

# ── Orders ────────────────────────────────────────────────────────────────────
st.subheader("Orders")
orders = load("SELECT * FROM orders ORDER BY created_at DESC")

if not orders.empty:
    def _color_status(val):
        colors = {"filled": "green", "pending": "goldenrod", "canceled": "red", "expired": "red"}
        color = colors.get(val, "gray")
        return f"color: {color}; font-weight: bold"

    styled = (
        orders
        .drop(columns=["updated_at"], errors="ignore")
        .style.map(_color_status, subset=["status"])
    )
    st.dataframe(styled, use_container_width=True)
else:
    st.info("No orders yet.")

st.divider()

# ── Signals ───────────────────────────────────────────────────────────────────
st.subheader("Signals")
sigs = load("SELECT * FROM signals ORDER BY timestamp DESC")

if not sigs.empty:
    sigs["approved"] = sigs["approved"].map({1: "✓ approved", 0: "✗ rejected"})

    def _color_approved(val):
        return "color: green" if val.startswith("✓") else "color: red"

    styled_sigs = sigs.style.map(_color_approved, subset=["approved"])
    st.dataframe(styled_sigs, use_container_width=True)
else:
    st.info("No signals yet.")

time.sleep(60)
st.rerun()
