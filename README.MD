# CSV Filter Dashboard

A Streamlit dashboard for visualizing and filtering CSV data with map integration.

## Features
- Interactive map visualization with markers and heatmap options
- Data filtering by subdivision and status
- Live tracking capabilities
- Multiple basemap styles
- Responsive design

## Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `streamlit run main.py`

## Data
The dashboard expects two CSV files:
- dtn.csv: DTN defect data
- tec.csv: ATGMS defect data

Each CSV should contain columns for Latitude, Longitude, and Subdivision.

In reality these defects have been filtered with bullshit and randomization for testing purposes