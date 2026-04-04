from __future__ import annotations

import gspread
import pandas as pd
import streamlit as st
from gspread.exceptions import WorksheetNotFound

from data_utils import build_lifting_seed_data, normalize_lifting_dataframe


def main() -> None:
    secrets = dict(st.secrets["connections"]["gsheets"])
    spreadsheet_url = secrets.pop("spreadsheet")
    secrets.pop("worksheet", None)

    client = gspread.service_account_from_dict(secrets)
    spreadsheet = client.open_by_url(spreadsheet_url)

    try:
        worksheet = spreadsheet.worksheet("lifting_maxes")
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="lifting_maxes", rows=100, cols=3)

    df = normalize_lifting_dataframe(build_lifting_seed_data())
    worksheet.clear()
    worksheet.update([df.columns.tolist()] + df.astype(str).values.tolist())

    st.write(
        {
            "status": "lifting_maxes_ready",
            "rows": len(df),
            "worksheet": "lifting_maxes",
        }
    )


if __name__ == "__main__":
    main()
