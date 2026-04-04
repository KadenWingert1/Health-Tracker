from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


LATEST_ENTRY_DATE = date(2026, 4, 3)
STOP_ENTRY_DATE = date(2021, 5, 1)
STOP_ENTRY_WEIGHT = 134.0


@dataclass(frozen=True)
class WeightEntry:
    entry_date: date
    weight: float


def load_myfitnesspal_rows(json_path: str | Path) -> list[dict]:
    payload = json.loads(Path(json_path).read_text())
    return payload["outcome"]["results"]


def clean_myfitnesspal_data(json_path: str | Path) -> pd.DataFrame:
    raw_rows = load_myfitnesspal_rows(json_path)

    cleaned_entries: list[WeightEntry] = []
    year = LATEST_ENTRY_DATE.year
    newer_month = LATEST_ENTRY_DATE.month

    for row in reversed(raw_rows):
        month_str, day_str = row["date"].split("/")
        month = int(month_str)
        day = int(day_str)

        if month > newer_month:
            year -= 1

        newer_month = month
        weight = float(row["total"])

        if weight == 0:
            continue

        entry_date = date(year, month, day)
        cleaned_entries.append(WeightEntry(entry_date=entry_date, weight=weight))

        if (
            entry_date == STOP_ENTRY_DATE
            and weight == STOP_ENTRY_WEIGHT
        ):
            break

    if not cleaned_entries:
        raise ValueError("No cleaned entries were produced from the MyFitnessPal export.")

    if cleaned_entries[-1].entry_date != STOP_ENTRY_DATE or cleaned_entries[-1].weight != STOP_ENTRY_WEIGHT:
        raise ValueError(
            "Expected to stop at the 2021-05-01 entry with weight 134. "
            "Please verify the source JSON before importing."
        )

    cleaned_entries.reverse()
    df = pd.DataFrame(
        {
            "date": [entry.entry_date.isoformat() for entry in cleaned_entries],
            "weight": [entry.weight for entry in cleaned_entries],
        }
    )
    return df


def normalize_sheet_dataframe(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "weight"])

    normalized = df.copy()
    normalized = normalized.rename(columns={col: col.strip().lower() for col in normalized.columns})

    if "date" not in normalized.columns or "weight" not in normalized.columns:
        available = ", ".join(normalized.columns.astype(str))
        raise ValueError(f"Google Sheet must contain 'date' and 'weight' columns. Found: {available}")

    normalized = normalized[["date", "weight"]].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
    normalized["weight"] = pd.to_numeric(normalized["weight"], errors="coerce")
    normalized = normalized.dropna(subset=["date", "weight"])
    normalized = normalized.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    normalized["date"] = normalized["date"].map(lambda value: value.isoformat())
    normalized["weight"] = normalized["weight"].astype(float).round(1)
    normalized.reset_index(drop=True, inplace=True)
    return normalized


def normalize_lifting_dataframe(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "lift", "max_weight"])

    normalized = df.copy()
    normalized = normalized.rename(columns={col: col.strip().lower() for col in normalized.columns})

    required_columns = {"date", "lift", "max_weight"}
    if not required_columns.issubset(normalized.columns):
        available = ", ".join(normalized.columns.astype(str))
        raise ValueError(
            "Google Sheet must contain 'date', 'lift', and 'max_weight' columns. "
            f"Found: {available}"
        )

    normalized = normalized[["date", "lift", "max_weight"]].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
    normalized["lift"] = normalized["lift"].astype(str).str.strip()
    normalized["max_weight"] = pd.to_numeric(normalized["max_weight"], errors="coerce")
    normalized = normalized.dropna(subset=["date", "lift", "max_weight"])
    normalized = normalized[normalized["lift"] != ""]
    normalized = normalized.sort_values(["lift", "date"]).drop_duplicates(
        subset=["lift", "date"], keep="last"
    )
    normalized["date"] = normalized["date"].map(lambda value: value.isoformat())
    normalized["lift"] = normalized["lift"].str.title()
    normalized["max_weight"] = normalized["max_weight"].astype(float).round(1)
    normalized.reset_index(drop=True, inplace=True)
    return normalized


def filter_range(df: pd.DataFrame, range_key: str) -> pd.DataFrame:
    normalized = normalize_sheet_dataframe(df)
    if normalized.empty or range_key == "All Time":
        return normalized

    max_date = datetime.strptime(normalized["date"].max(), "%Y-%m-%d").date()
    days_lookup = {
        "Week": 7,
        "Month": 30,
        "Year": 365,
    }
    days = days_lookup.get(range_key)
    if days is None:
        return normalized

    cutoff = max_date - timedelta(days=days - 1)
    return normalized[pd.to_datetime(normalized["date"]).dt.date >= cutoff].reset_index(drop=True)


def build_lifting_seed_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": "2023-08-11", "lift": "Deadlift", "max_weight": 325},
            {"date": "2023-10-21", "lift": "Squat", "max_weight": 265},
            {"date": "2023-10-22", "lift": "Bench", "max_weight": 185},
            {"date": "2023-11-25", "lift": "Bench", "max_weight": 190},
            {"date": "2024-03-23", "lift": "Squat", "max_weight": 265},
            {"date": "2024-03-25", "lift": "Bench", "max_weight": 195},
            {"date": "2025-08-14", "lift": "Squat", "max_weight": 245},
            {"date": "2025-08-16", "lift": "Bench", "max_weight": 195},
            {"date": "2025-08-17", "lift": "Deadlift", "max_weight": 305},
        ]
    )
