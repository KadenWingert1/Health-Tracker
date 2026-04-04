from __future__ import annotations

import streamlit as st
from streamlit_gsheets import GSheetsConnection

from data_utils import clean_myfitnesspal_data


def main() -> None:
    df = clean_myfitnesspal_data("myfitnesspal.json")
    connection = st.connection("gsheets", type=GSheetsConnection)
    connection.update(worksheet="weights", data=df)
    st.write(
        {
            "status": "uploaded",
            "rows": len(df),
            "start_date": df["date"].min(),
            "end_date": df["date"].max(),
        }
    )


if __name__ == "__main__":
    main()
