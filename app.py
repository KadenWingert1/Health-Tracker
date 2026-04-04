from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from gspread.exceptions import WorksheetNotFound
from streamlit_gsheets import GSheetsConnection

from data_utils import (
    filter_range,
    normalize_lifting_dataframe,
    normalize_sheet_dataframe,
)


TEXT_COLOR = "#31333F"
BG_COLOR = "#FFFFFF"
SECONDARY_BG = "#F0F2F6"
ACCENT = "#2563EB"
ACCENT_DARK = "#1D4ED8"
BORDER = "#D0D5DD"


st.set_page_config(page_title="Health Tracker", page_icon="🏋️", layout="centered")

st.markdown(
    f"""
    <style>
        .stApp {{
            background: {BG_COLOR};
            color: {TEXT_COLOR};
        }}
        .block-container {{
            max-width: 760px;
            padding-top: 1rem;
            padding-bottom: 4rem;
        }}
        html, body, [class*="css"] {{
            color: {TEXT_COLOR};
        }}
        h1, h2, h3, p, label, span, div {{
            color: {TEXT_COLOR};
        }}
        div[data-testid="stForm"],
        div[data-testid="stMetric"],
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {{
            background: {BG_COLOR};
            border: 1px solid {BORDER};
            border-radius: 16px;
        }}
        div[data-testid="stMetric"] {{
            padding: 0.85rem;
        }}
        section[data-testid="stSidebar"] {{
            background: {SECONDARY_BG};
        }}
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea,
        input {{
            background: {BG_COLOR} !important;
            color: {TEXT_COLOR} !important;
            border-color: #98A2B3 !important;
        }}
        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stButton"] button {{
            background: {ACCENT};
            color: #FFFFFF;
            border-radius: 999px;
            border: none;
            min-height: 3rem;
            font-weight: 700;
        }}
        div[data-testid="stFormSubmitButton"] button:hover,
        div[data-testid="stButton"] button:hover {{
            background: {ACCENT_DARK};
            color: #FFFFFF;
        }}
        button[kind="secondary"] {{
            background: {SECONDARY_BG};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_connection() -> GSheetsConnection:
    return st.connection("gsheets", type=GSheetsConnection)


def load_weights() -> pd.DataFrame:
    data = get_connection().read(worksheet="weights", usecols=[0, 1], ttl=0)
    return normalize_sheet_dataframe(data)


def save_weights(df: pd.DataFrame) -> None:
    get_connection().update(worksheet="weights", data=normalize_sheet_dataframe(df))


def load_lifts() -> pd.DataFrame:
    try:
        data = get_connection().read(worksheet="lifting_maxes", ttl=0)
    except WorksheetNotFound:
        return pd.DataFrame(columns=["date", "lift", "max_weight"])
    return normalize_lifting_dataframe(data)


def save_lifts(df: pd.DataFrame) -> None:
    get_connection().update(worksheet="lifting_maxes", data=normalize_lifting_dataframe(df))


def add_or_replace_today_weight(weight_value: float) -> None:
    existing = load_weights()
    today_iso = date.today().isoformat()
    new_row = pd.DataFrame([{"date": today_iso, "weight": float(weight_value)}])
    save_weights(pd.concat([existing, new_row], ignore_index=True))


def add_lift_entry(lift_name: str, lift_weight: float, lift_date: date) -> None:
    existing = load_lifts()
    new_row = pd.DataFrame(
        [{"date": lift_date.isoformat(), "lift": lift_name, "max_weight": float(lift_weight)}]
    )
    save_lifts(pd.concat([existing, new_row], ignore_index=True))


def themed_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    y_label: str = "",
) -> None:
    fig = px.line(df, x=x, y=y, color=color, markers=True, labels={y: y_label, x: "Date"})
    fig.update_traces(line={"width": 3}, marker={"size": 8})
    fig.update_layout(
        height=360,
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        font={"color": TEXT_COLOR},
        legend_title_text="",
        margin={"l": 18, "r": 18, "t": 18, "b": 18},
        yaxis_title=y_label,
        xaxis_title=None,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E4E7EC")
    st.plotly_chart(fig, use_container_width=True)


def calculate_weight_insights(df: pd.DataFrame) -> dict[str, str]:
    ordered = df.copy()
    ordered["weight"] = pd.to_numeric(ordered["weight"])
    latest = ordered.iloc[-1]
    previous = ordered.iloc[-2] if len(ordered) > 1 else None
    rolling_week = ordered.tail(min(7, len(ordered)))
    rolling_month = ordered.tail(min(30, len(ordered)))

    insights = {
        "Latest Weight": f"{latest['weight']:.1f} lb",
        "7-Day Avg": f"{rolling_week['weight'].mean():.1f} lb",
        "30-Day Change": f"{(latest['weight'] - rolling_month.iloc[0]['weight']):+.1f} lb",
    }
    if previous is not None:
        insights["Since Last Entry"] = f"{(latest['weight'] - previous['weight']):+.1f} lb"
    return insights


def calculate_lift_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    ordered = df.copy()
    ordered["date"] = pd.to_datetime(ordered["date"])
    ordered["max_weight"] = pd.to_numeric(ordered["max_weight"])
    latest = ordered.sort_values("date").groupby("lift", as_index=False).tail(1)
    latest = latest.sort_values("lift")[["lift", "max_weight", "date"]]
    latest["date"] = latest["date"].dt.strftime("%Y-%m-%d")
    latest.rename(columns={"max_weight": "Current Max", "date": "Latest Date"}, inplace=True)
    return latest.reset_index(drop=True)


def render_lift_rows(summary_df: pd.DataFrame) -> None:
    if summary_df.empty:
        return

    for row in summary_df.to_dict("records"):
        st.markdown(
            f"""
            <div style="
                background: {BG_COLOR};
                border: 1px solid {BORDER};
                border-radius: 16px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.75rem;
            ">
                <div style="font-size: 0.95rem; font-weight: 700; color: {TEXT_COLOR};">{row['lift']}</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: {TEXT_COLOR};">{row['Current Max']:.0f} lb</div>
                <div style="font-size: 0.9rem; color: {TEXT_COLOR};">Latest PR date: {row['Latest Date']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.title("Health Tracker")
st.caption("Accessible, mobile-friendly tracking for bodyweight and strength.")

weights_tab, lifts_tab = st.tabs(["Weight", "Lifting Maxes"])

with weights_tab:
    with st.form("add_weight_form", clear_on_submit=True):
        st.subheader("Add Today's Weight")
        weight_input = st.number_input(
            "Weight (lb)",
            min_value=1.0,
            max_value=1000.0,
            value=None,
            step=0.1,
            placeholder="149.2",
        )
        weight_submitted = st.form_submit_button("Save Weight")

    if weight_submitted:
        if weight_input is None:
            st.error("Enter a weight before saving.")
        else:
            add_or_replace_today_weight(weight_input)
            st.success(f"Saved today's weight: {weight_input:.1f} lb")
            st.rerun()

    weights_df = load_weights()
    if weights_df.empty:
        st.warning("No weight entries found in the `weights` worksheet yet.")
    else:
        insight_columns = st.columns(2)
        insights = list(calculate_weight_insights(weights_df).items())
        for index, (label, value) in enumerate(insights):
            insight_columns[index % 2].metric(label, value)

        range_key = st.segmented_control(
            "Weight Chart Range",
            options=["Week", "Month", "Year", "All Time"],
            default="Month",
            selection_mode="single",
        )
        weight_chart_df = filter_range(weights_df, range_key).copy()
        weight_chart_df["date"] = pd.to_datetime(weight_chart_df["date"])
        themed_line_chart(weight_chart_df, x="date", y="weight", y_label="Weight (lb)")

    st.subheader("Edit Weight Entries")
    editable_weights = weights_df.copy()
    if not editable_weights.empty:
        editable_weights["date"] = pd.to_datetime(editable_weights["date"], errors="coerce")

    edited_weights = st.data_editor(
        editable_weights,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", required=True),
            "weight": st.column_config.NumberColumn(
                "Weight (lb)", min_value=1.0, max_value=1000.0, step=0.1, required=True
            ),
        },
    )

    if st.button("Save Weight Table", use_container_width=True):
        try:
            to_save = edited_weights.copy()
            to_save["date"] = pd.to_datetime(to_save["date"], errors="coerce").dt.date
            to_save["date"] = to_save["date"].map(
                lambda value: value.isoformat() if pd.notna(value) else None
            )
            save_weights(to_save)
        except Exception as exc:
            st.error(f"Could not save weight changes: {exc}")
        else:
            st.success("Weight sheet updated successfully.")
            st.rerun()

with lifts_tab:
    with st.form("add_lift_form", clear_on_submit=True):
        st.subheader("Add a New Lift Max")
        lift_name = st.selectbox("Lift", ["Bench", "Squat", "Deadlift"])
        lift_weight = st.number_input(
            "Max Weight (lb)",
            min_value=1.0,
            max_value=2000.0,
            value=None,
            step=5.0,
            placeholder="225",
        )
        lift_date = st.date_input("Date", value=date.today())
        lift_submitted = st.form_submit_button("Save Lift Max")

    if lift_submitted:
        if lift_weight is None:
            st.error("Enter a max weight before saving.")
        else:
            add_lift_entry(lift_name, lift_weight, lift_date)
            st.success(f"Saved {lift_name} max at {lift_weight:.0f} lb.")
            st.rerun()

    lifts_df = load_lifts()
    if lifts_df.empty:
        st.info(
            "No data found in the `lifting_maxes` worksheet yet. "
            "Run `python3 -m streamlit run setup_strength_sheet.py` once to create and seed it."
        )
    else:
        lift_summary = calculate_lift_summary(lifts_df)
        render_lift_rows(lift_summary)

        selected_lifts = st.multiselect(
            "Show lifts on chart",
            options=["Bench", "Squat", "Deadlift"],
            default=["Bench", "Squat", "Deadlift"],
            key="chart_lift_selector",
        )

        filtered_lifts = lifts_df[lifts_df["lift"].isin(selected_lifts)].copy()
        if filtered_lifts.empty:
            st.info("Select at least one lift to show its history.")
        else:
            chart_lifts = filtered_lifts.copy()
            chart_lifts["date"] = pd.to_datetime(chart_lifts["date"])
            themed_line_chart(
                chart_lifts.sort_values(["lift", "date"]),
                x="date",
                y="max_weight",
                color="lift",
                y_label="Max Weight (lb)",
            )

        st.subheader("Lifting History")
        history_selection = st.multiselect(
            "Choose lifts to view and edit",
            options=["Bench", "Squat", "Deadlift"],
            default=["Bench", "Squat", "Deadlift"],
            key="history_lift_selector",
        )
        visible_lifts = lifts_df[lifts_df["lift"].isin(history_selection)].copy()
        st.dataframe(
            visible_lifts.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Edit Lifting Entries")
    editable_lifts = lifts_df.copy()
    if not editable_lifts.empty:
        selected_for_editing = st.multiselect(
            "Choose lifts to edit",
            options=["Bench", "Squat", "Deadlift"],
            default=["Bench", "Squat", "Deadlift"],
            key="edit_lift_selector",
        )
        editable_lifts = editable_lifts[editable_lifts["lift"].isin(selected_for_editing)].copy()

    if not editable_lifts.empty:
        editable_lifts["date"] = pd.to_datetime(editable_lifts["date"], errors="coerce")

    edited_lifts = st.data_editor(
        editable_lifts,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", required=True),
            "lift": st.column_config.SelectboxColumn(
                "Lift", options=["Bench", "Squat", "Deadlift"], required=True
            ),
            "max_weight": st.column_config.NumberColumn(
                "Max Weight (lb)", min_value=1.0, max_value=2000.0, step=5.0, required=True
            ),
        },
    )

    if st.button("Save Lifting Table", use_container_width=True):
        try:
            edited_subset = edited_lifts.copy()
            edited_subset["date"] = pd.to_datetime(edited_subset["date"], errors="coerce").dt.date
            edited_subset["date"] = edited_subset["date"].map(
                lambda value: value.isoformat() if pd.notna(value) else None
            )

            full_dataset = load_lifts()
            untouched_rows = full_dataset[~full_dataset["lift"].isin(selected_for_editing)].copy()
            combined = pd.concat([untouched_rows, edited_subset], ignore_index=True)
            save_lifts(combined)
        except Exception as exc:
            st.error(f"Could not save lifting changes: {exc}")
        else:
            st.success("Lifting sheet updated successfully.")
            st.rerun()
