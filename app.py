import pandas as pd
import streamlit as st
import folium
from folium import Map, Marker
from folium.plugins import HeatMap, MarkerCluster, LocateControl
from streamlit_folium import folium_static

# Constants
SUBDIVISIONS = ["HARDISTY", "SUTHERLAND", "WILKIE", "WYNYARD"]


@st.cache_data
def load_data():
    """Load and cache CSV data"""
    try:
        return pd.read_csv("dtn.csv"), pd.read_csv("tec.csv")
    except FileNotFoundError as e:
        st.error(f"Error: {e}")
        return None, None


def create_tooltip(row, defect_type="DTN"):
    """
    Create tooltip HTML for map markers, displaying ALL columns in the row.
    """
    # Start with a header indicating defect type
    tooltip_html = f"<b>{defect_type.upper()} Defect</b><br>"

    # Use a table format for readability
    tooltip_html += "<table>"
    for col in row.index:
        val = row[col]
        tooltip_html += f"<tr><td><b>{col}</b></td><td>{val}</td></tr>"
    tooltip_html += "</table>"

    return tooltip_html


def process_coordinates(df):
    """Process coordinate data efficiently"""
    return df[['Latitude', 'Longitude']].dropna().values.tolist()


def create_map(dtn_df, tec_df, map_view_mode="markers", basemap_style="OpenStreetMap"):
    """Create an enhanced folium map with markers/heatmap for DTN and TEC points"""
    # Calculate center point efficiently
    all_coords = pd.concat([
        dtn_df[['Latitude', 'Longitude']].dropna(),
        tec_df[['Latitude', 'Longitude']].dropna()
    ])

    center_lat = all_coords['Latitude'].mean() if not all_coords.empty else 52.9399
    center_lon = all_coords['Longitude'].mean() if not all_coords.empty else -108.4976

    # Create base map
    m = Map(location=[center_lat, center_lon], zoom_start=7, tiles=basemap_style)

    if map_view_mode == "markers":
        # Create marker clusters
        dtn_cluster = MarkerCluster(name="DTN Defects", disableClusteringAtZoom=13).add_to(m)
        tec_cluster = MarkerCluster(name="ATGMS Defects", disableClusteringAtZoom=13).add_to(m)

        # Add markers for DTN
        if {'Latitude', 'Longitude'}.issubset(dtn_df.columns):
            for _, row in dtn_df.dropna(subset=['Latitude', 'Longitude']).iterrows():
                Marker(
                    location=[row['Latitude'], row['Longitude']],
                    tooltip=create_tooltip(row, "DTN"),
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(dtn_cluster)

        # Add markers for TEC
        if {'Latitude', 'Longitude'}.issubset(tec_df.columns):
            for _, row in tec_df.dropna(subset=['Latitude', 'Longitude']).iterrows():
                Marker(
                    location=[row['Latitude'], row['Longitude']],
                    tooltip=create_tooltip(row, "TEC"),
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(tec_cluster)

    else:  # Heatmap view
        heat_data = process_coordinates(dtn_df) + process_coordinates(tec_df)
        if heat_data:
            HeatMap(heat_data).add_to(m)

    # Add location control
    LocateControl(
        auto_start=False,
        keepCurrentZoomLevel=True,
        flyTo=False,
        drawCircle=True,
        locateOptions={
            'enableHighAccuracy': True,
            'setView': False,
            'watch': True,
            'maxZoom': 16,
            'maximumAge': 60000
        }
    ).add_to(m)

    return m


def filter_dataframe(df, filters):
    """Apply filters to DataFrame efficiently"""
    for column, value in filters.items():
        if value != "All" and column in df.columns:
            df = df[df[column] == value]
    return df


def create_sidebar_filters(df, prefix, filter_columns, default_values=None):
    """Create sidebar filters for a DataFrame with default values"""
    filters = {}
    default_values = default_values or {}

    for col in filter_columns:
        if col in df.columns:
            unique_values = ["All"] + list(df[col].unique())
            default_value = default_values.get(col, "All")
            try:
                default_index = unique_values.index(default_value)
            except ValueError:
                default_index = 0

            selected = st.sidebar.selectbox(
                f"Select {prefix} {col}:",
                options=unique_values,
                index=default_index
            )
            filters[col] = selected
    return filters


def rearrange_columns(df, priority_columns):
    """Rearrange DataFrame columns efficiently"""
    available_cols = [col for col in priority_columns if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in priority_columns]
    return df[available_cols + remaining_cols]


def main():
    # Page setup
    st.set_page_config(layout="wide", page_title="CSV Filter Dashboard")
    st.title("Curated DTN and ATGMS Defect Dashboard - Orgo Nag")

    # Initialize session state
    if "live_tracking" not in st.session_state:
        st.session_state["live_tracking"] = False

    # Load data
    dtn_df, tec_df = load_data()
    if dtn_df is None or tec_df is None:
        return

    # Subdivision selection
    subdivision_choice = st.selectbox("Select a Subdivision to View:", SUBDIVISIONS)

    # Filter by subdivision
    if "Subdivision" in dtn_df.columns and "Subdivision" in tec_df.columns:
        filtered_dtn_df = dtn_df[dtn_df["Subdivision"] == subdivision_choice]
        filtered_tec_df = tec_df[tec_df["Subdivision"] == subdivision_choice]
    else:
        st.error("Error: 'Subdivision' column not found in one or both datasets.")
        return

    # Sidebar filters
    st.sidebar.header("Filter Options")

    # Define default filters
    dtn_default_filters = {
        "Status": "Open"
    }

    tec_default_filters = {
        "Status": "Confirmed",
        "Sys": "TGMS",
        "Severity": "Urgent"
    }

    # DTN Filters
    st.sidebar.subheader("DTN Filters")
    dtn_filters = create_sidebar_filters(
        filtered_dtn_df,
        "DTN",
        ["Status", "Asset"],
        default_values=dtn_default_filters
    )
    filtered_dtn_df = filter_dataframe(filtered_dtn_df, dtn_filters)

    # TEC Filters
    st.sidebar.subheader("TEC Filters")
    tec_filters = create_sidebar_filters(
        filtered_tec_df,
        "TEC",
        ["Status", "Sys", "Severity"],
        default_values=tec_default_filters
    )
    filtered_tec_df = filter_dataframe(filtered_tec_df, tec_filters)

    # Rearrange columns
    dtn_priority_cols = [
        "MP", "Asset Type", "Asset", "Defect Date", "Comment",
        "Reg Rule", "Reg Rule Description", "Status", "Action"
    ]
    tec_priority_cols = [
        "MP", "Linecode", "Date Time", "Sys", "Severity",
        "Type", "Value", "Length", "Status"
    ]

    rearranged_dtn_df = rearrange_columns(filtered_dtn_df, dtn_priority_cols)
    rearranged_tec_df = rearrange_columns(filtered_tec_df, tec_priority_cols)

    # Map configuration
    st.sidebar.markdown("---")
    st.sidebar.subheader("Map Settings")

    map_view_mode = st.sidebar.radio(
        "Select Map View",
        ("markers", "heatmap"),
        format_func=lambda x: "Scatter Plot (Markers)" if x == "markers" else "Heatmap"
    )

    basemap_options = {
        "Street (OpenStreetMap)": "OpenStreetMap",
        "Light (CartoDB positron)": "CartoDB positron",
        "Dark (CartoDB dark_matter)": "CartoDB dark_matter",
        "Topographic (OpenTopoMap)": "OpenTopoMap"
    }
    basemap_choice = st.sidebar.selectbox(
        "Select Basemap Style",
        list(basemap_options.keys()),
        index=0
    )

    # Live tracking controls
    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("Start Live Tracking"):
            st.session_state["live_tracking"] = True
    with col2:
        if st.button("Stop Live Tracking"):
            st.session_state["live_tracking"] = False

    # Reset filters
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Filters"):
        st.experimental_rerun()

    # Map visualization
    with st.expander("Map Visualization", expanded=True):
        if {'Latitude', 'Longitude'}.issubset(rearranged_dtn_df.columns) or \
                {'Latitude', 'Longitude'}.issubset(rearranged_tec_df.columns):

            # Use custom CSS to ensure the map container spans the full width
            st.markdown(
                """
                <style>
                    .element-container {
                        width: 100% !important;
                    }
                    .stMarkdown {
                        width: 100% !important;
                    }
                    iframe {
                        width: 100% !important;
                    }
                </style>
                """,
                unsafe_allow_html=True
            )

            map_obj = create_map(
                rearranged_dtn_df,
                rearranged_tec_df,
                map_view_mode,
                basemap_options[basemap_choice]
            )

            # Display the map with full width
            folium_static(map_obj, width=1600, height=600)

            st.markdown(
                "**Note**: If you do not see your location on the map, make sure to allow location "
                "permissions in your browser and that you are running this app over HTTPS or localhost."
            )
        else:
            st.warning("No coordinate data available for mapping.")

    # Display filtered data
    st.header(f"Filtered Data for Subdivision: {subdivision_choice}")

    st.subheader("DTN Defects (Rearranged)")
    st.markdown(f"**Total Rows: {len(rearranged_dtn_df)}**")
    st.dataframe(rearranged_dtn_df)

    st.subheader("ATGMS Defects (Rearranged)")
    st.markdown(f"**Total Rows: {len(rearranged_tec_df)}**")
    st.dataframe(rearranged_tec_df)


if __name__ == "__main__":
    main()
