"""
EnergyLens — Energy Waste & Cost Audit Tool
Built by Avika Bhardwaj

Problem this solves:
Small businesses (shops, workshops, small manufacturing units) often have
smart meter or inverter data sitting unused. They have no easy, free way to
find out WHEN they waste energy and HOW MUCH money/CO2 they could save by
shifting usage to off-peak hours. This app takes a raw timestamp + energy
reading CSV and turns it into a clear, actionable audit.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="EnergyLens — Energy Waste Audit",
    page_icon="⚡",
    layout="wide",
)

# India CEA grid emission factor (kg CO2 per kWh) — public data point
EMISSION_FACTOR = 0.716  # kg CO2 / kWh (India, CEA CO2 baseline database, approx)

# Simple flat tariff assumption (editable by user) for cost estimates
DEFAULT_TARIFF = 8.0  # INR per kWh

# Peak hours definition (commercial/industrial peak, typical Indian DISCOM slabs)
PEAK_HOURS = list(range(9, 12)) + list(range(18, 22))  # 9-12, 18-22


# ----------------------------
# HELPERS
# ----------------------------
def load_and_validate(file) -> tuple[pd.DataFrame | None, str | None]:
    """Load CSV, find timestamp + energy columns, validate, return clean df or error."""
    try:
        df = pd.read_csv(file)
    except Exception as e:
        return None, f"Could not read file as CSV: {e}"

    if df.empty:
        return None, "The file is empty."

    cols_lower = {c.lower().strip(): c for c in df.columns}

    # try to find timestamp column
    ts_candidates = ["timestamp", "date", "datetime", "time", "date_time"]
    ts_col = next((cols_lower[c] for c in ts_candidates if c in cols_lower), None)

    # try to find energy column
    energy_candidates = [
        "energy_kwh", "energy", "kwh", "consumption", "usage",
        "power", "load", "energy_consumption"
    ]
    energy_col = next((cols_lower[c] for c in energy_candidates if c in cols_lower), None)

    if ts_col is None or energy_col is None:
        return None, (
            "Couldn't find the right columns. Your file needs a timestamp column "
            "(e.g. 'timestamp', 'date') and an energy column (e.g. 'energy_kwh', 'usage'). "
            f"Found columns: {list(df.columns)}"
        )

    df = df[[ts_col, energy_col]].copy()
    df.columns = ["timestamp", "energy_kwh"]

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["timestamp"])
    dropped_ts = before - len(df)

    df["energy_kwh"] = pd.to_numeric(df["energy_kwh"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["energy_kwh"])
    dropped_val = before - len(df)

    df = df[df["energy_kwh"] >= 0]  # drop negative readings (sensor errors)

    if df.empty:
        return None, "After cleaning, no valid rows remained. Check your data format."

    df = df.sort_values("timestamp").reset_index(drop=True)

    notes = []
    if dropped_ts:
        notes.append(f"{dropped_ts} rows had unreadable timestamps and were dropped.")
    if dropped_val:
        notes.append(f"{dropped_val} rows had non-numeric/missing energy values and were dropped.")

    df.attrs["cleaning_notes"] = notes
    return df, None


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["dayofweek"] >= 5
    df["day_type"] = np.where(df["is_weekend"], "Weekend", "Weekday")
    df["is_peak"] = df["hour"].isin(PEAK_HOURS)
    df["date"] = df["timestamp"].dt.date
    return df


def compute_insights(df: pd.DataFrame, tariff: float) -> dict:
    weekday_avg = df.loc[~df["is_weekend"], "energy_kwh"].mean()
    weekend_avg = df.loc[df["is_weekend"], "energy_kwh"].mean()
    pct_diff = ((weekday_avg - weekend_avg) / weekend_avg * 100) if weekend_avg else np.nan

    hourly_avg = df.groupby("hour")["energy_kwh"].mean()
    peak_hour = int(hourly_avg.idxmax())
    peak_value = hourly_avg.max()

    total_kwh = df["energy_kwh"].sum()
    total_cost = total_kwh * tariff
    total_co2 = total_kwh * EMISSION_FACTOR

    peak_kwh = df.loc[df["is_peak"], "energy_kwh"].sum()
    offpeak_kwh = df.loc[~df["is_peak"], "energy_kwh"].sum()
    peak_share = (peak_kwh / total_kwh * 100) if total_kwh else 0

    # Savings potential: assume 20% of peak-hour load could realistically be
    # shifted to off-peak without affecting operations (a conservative,
    # commonly-cited industrial demand-response assumption)
    shiftable_pct = 0.20
    shiftable_kwh = peak_kwh * shiftable_pct
    cost_savings = shiftable_kwh * tariff * 0.15  # assume 15% tariff discount off-peak (typical ToD tariff structure)
    co2_note_kwh = shiftable_kwh  # CO2 doesn't reduce by shifting, only by reducing total use; flagged separately

    return {
        "weekday_avg": weekday_avg,
        "weekend_avg": weekend_avg,
        "pct_diff": pct_diff,
        "peak_hour": peak_hour,
        "peak_value": peak_value,
        "total_kwh": total_kwh,
        "total_cost": total_cost,
        "total_co2": total_co2,
        "peak_share": peak_share,
        "shiftable_kwh": shiftable_kwh,
        "cost_savings": cost_savings,
        "hourly_avg": hourly_avg,
        "days_covered": df["date"].nunique(),
    }


def generate_sample_data() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=24 * 90, freq="h")
    usage = []
    for d in dates:
        hour = d.hour
        is_weekend = d.dayofweek >= 5
        if is_weekend:
            base = 12 + np.random.normal(0, 2)
        else:
            if 8 <= hour <= 18:
                base = 45 + np.random.normal(0, 5)
                if hour == 9:
                    base += 15
            elif 19 <= hour <= 22:
                base = 20 + np.random.normal(0, 3)
            else:
                base = 8 + np.random.normal(0, 2)
        usage.append(max(base, 0))
    return pd.DataFrame({"timestamp": dates, "energy_kwh": usage})


# ----------------------------
# UI
# ----------------------------
st.title("⚡ EnergyLens")
st.caption("Find out when your business wastes energy — and what it's costing you.")

with st.expander("ℹ️ What is this and how does it work?", expanded=False):
    st.markdown(
        """
**The problem:** Small businesses with smart meters or inverter logs have energy
data sitting unused on a memory card or a portal export. There's no free, simple
way to turn that raw data into "here's what to change."

**What this tool does:** Upload a CSV with a timestamp column and an energy
(kWh) column. EnergyLens analyzes your weekday vs weekend usage, finds your
peak demand hour, estimates your electricity cost and CO₂ footprint, and
shows how much you could save by shifting load off-peak.

**Don't have data?** Use the sample dataset below — it simulates a small
manufacturing unit's hourly meter readings over 90 days.
        """
    )

st.divider()

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader(
        "Upload your energy usage CSV (must have a timestamp + energy/kWh column)",
        type=["csv"],
    )
with col2:
    use_sample = st.button("Use sample dataset instead", use_container_width=True)

tariff = st.sidebar.number_input(
    "Your electricity tariff (₹/kWh)", min_value=1.0, max_value=30.0,
    value=DEFAULT_TARIFF, step=0.5,
    help="Used to estimate cost. Defaults to a typical Indian commercial tariff."
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Peak hours assumed:** 9–12 PM and 6–10 PM\n\n"
    "*(typical commercial Time-of-Day peak slab in most Indian states — "
    "adjust your interpretation if your DISCOM differs)*"
)
st.sidebar.markdown("---")
st.sidebar.markdown("Built by **Avika Bhardwaj** · [GitHub](https://github.com/) ")

df_raw = None
source_label = None

if use_sample:
    df_raw = generate_sample_data()
    source_label = "sample dataset (simulated small manufacturing unit, 90 days)"
elif uploaded_file is not None:
    df_raw, err = load_and_validate(uploaded_file)
    if err:
        st.error(f"⚠️ {err}")
    else:
        source_label = uploaded_file.name

if df_raw is not None:
    cleaning_notes = df_raw.attrs.get("cleaning_notes", [])
    for note in cleaning_notes:
        st.warning(f"🧹 Data cleaning: {note}")

    df = enrich(df_raw)
    insights = compute_insights(df, tariff)

    st.success(f"Analyzed **{len(df):,} readings** across **{insights['days_covered']} days** from {source_label}.")

    st.divider()
    st.subheader("📊 Key Numbers")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Energy Used", f"{insights['total_kwh']:,.0f} kWh")
    k2.metric("Estimated Cost", f"₹{insights['total_cost']:,.0f}")
    k3.metric("Estimated CO₂ Emitted", f"{insights['total_co2']:,.0f} kg")
    k4.metric("Peak Hour", f"{insights['peak_hour']}:00",
              f"{insights['peak_value']:.1f} kWh avg")

    st.divider()
    st.subheader("📈 Weekday vs Weekend Usage")
    wc1, wc2 = st.columns([1, 2])
    with wc1:
        st.metric("Weekday Avg", f"{insights['weekday_avg']:.1f} kWh/hr")
        st.metric("Weekend Avg", f"{insights['weekend_avg']:.1f} kWh/hr")
        if not np.isnan(insights['pct_diff']):
            diff_label = "higher" if insights['pct_diff'] >= 0 else "lower"
            st.metric("Difference", f"{abs(insights['pct_diff']):.0f}% {diff_label} on weekdays")
    with wc2:
        day_avg = df.groupby("day_type")["energy_kwh"].mean().reset_index()
        fig = px.bar(day_avg, x="day_type", y="energy_kwh",
                     color="day_type", text_auto=".1f",
                     labels={"energy_kwh": "Avg kWh", "day_type": ""},
                     color_discrete_sequence=["#2563eb", "#93c5fd"])
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🕐 Hourly Usage Pattern")
    hourly_df = insights["hourly_avg"].reset_index()
    hourly_df.columns = ["hour", "avg_kwh"]
    hourly_df["is_peak"] = hourly_df["hour"].isin(PEAK_HOURS)
    fig2 = px.bar(hourly_df, x="hour", y="avg_kwh", color="is_peak",
                  labels={"avg_kwh": "Avg kWh", "hour": "Hour of Day"},
                  color_discrete_map={True: "#ef4444", False: "#60a5fa"})
    fig2.update_layout(
        legend_title_text="",
        height=350,
        xaxis=dict(dtick=1),
    )
    fig2.for_each_trace(lambda t: t.update(name="Peak hour" if t.name == "True" else "Off-peak"))
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("💡 Recommendations")
    st.markdown(
        f"""
- **{insights['peak_share']:.0f}%** of your total energy use happens during peak hours
  (9–12 PM, 6–10 PM), when grid strain — and often tariffs — are highest.
- Your weekday usage is **{insights['pct_diff']:.0f}% higher** than weekend usage,
  which is expected, but check if any of that weekday load (lighting, HVAC,
  idle equipment) is running unnecessarily.
- If you shift just **20% of your peak-hour load** to off-peak hours (e.g.
  running non-urgent machinery overnight or early morning), you could save
  an estimated **₹{insights['cost_savings']:,.0f}** over this period under a typical
  Time-of-Day tariff structure.
- Shifting load reduces *cost*, not total emissions — to cut **CO₂**, the
  real lever is reducing total consumption (efficient equipment, switching
  off idle loads), not just timing.
        """
    )

    with st.expander("📋 View raw cleaned data"):
        st.dataframe(df[["timestamp", "energy_kwh", "day_type", "is_peak"]], use_container_width=True)

else:
    st.info("👆 Upload a CSV or click 'Use sample dataset' above to get started.")
