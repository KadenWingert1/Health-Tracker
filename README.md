# Weight Tracker

This Streamlit app is optimized for mobile use and stores weight data in a Google Sheet.

## Files

- `app.py`: mobile-friendly weight tracker UI
- `data_utils.py`: MyFitnessPal cleaning and Google Sheet normalization logic
- `import_mfp_to_gsheet.py`: one-time upload script for the cleaned historical data
- `setup_strength_sheet.py`: one-time setup script for the `lifting_maxes` worksheet and seed data
- `.streamlit/secrets.toml.example`: example secrets layout for Google Sheets credentials

## Setup

1. Install dependencies:
   `pip install -r requirements.txt`
2. Create a Google Cloud service account with Sheets access enabled.
3. Share your Google Sheet with the service account email as an editor.
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:
   - your Google Sheet URL
   - your service account JSON fields under the same `[connections.gsheets]` block
5. Run the one-time import:
   `streamlit run import_mfp_to_gsheet.py`
6. Create and seed the lifting worksheet:
   `streamlit run setup_strength_sheet.py`
7. Start the app:
   `streamlit run app.py`

## Google Sheet

Create a worksheet named `weights` with two columns:

- `date`
- `weight`

The import script will overwrite that worksheet with the cleaned MyFitnessPal history.

The lifting setup script creates a `lifting_maxes` worksheet with these columns:

- `date`
- `lift`
- `max_weight`
