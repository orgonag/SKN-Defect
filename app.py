import pandas as pd
import streamlit as st
import folium
from folium import Map, Marker
from folium.plugins import HeatMap, MarkerCluster, LocateControl
from streamlit_folium import folium_static

# This is a list of subdivisions to choose from
SUBDIVISIONS = ['HARDISTY', "SUTHERLAND", "WILKIE", "WYNYARD"]

@st.cache_data
def load_data():
    # Load the CSV files for DTN and TEC, return them as DataFrames
    try:
        return pd.read_csv("dtn.csv"), pd.read_csv("tec.csv")
    except FileNotFoundError as e:
        st.error(f"Error: {e}")
        return None, None

def create_popup_html(row, defect_type="DTN"):
    # Build HTML for the popup on the map marker
    popup_html = f"<b>{defect_type.upper()} Defect</b><br>"
    popup_html += "<table>"
    for col in row.index:
        val = row[col]
        popup_html += f"<tr><td><b>{col}</b></td><td>{val}</td></tr>"
    popup_html += "</table>"
    return popup_html

def process_coordinates(df):
    # Extract latitude and longitude to create a list of coordinate pairs
    return df[['Latitude', 'Longitude']].dropna().values.tolist()

def create_map(dtn_df, tec_df, map_view_mode="markers", basemap_choice=None):
    # Combine coordinates to find a central point for the map
    all_coords = pd.concat([
        dtn_df[['Latitude', 'Longitude']].dropna(),
        tec_df[['Latitude', 'Longitude']].dropna()
    ])

    center_lat = all_coords['Latitude'].mean() if not all_coords.empty else 52.9399
    center_lon = all_coords['Longitude'].mean() if not all_coords.empty else -108.4976

    # Check how the basemap was provided (string or dictionary)
    if isinstance(basemap_choice, str):
        m = Map(location=[center_lat, center_lon], zoom_start=7, tiles=basemap_choice)
    elif isinstance(basemap_choice, dict):
        m = Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles=basemap_choice["tiles"],
            attr=basemap_choice.get("attribution", "")
        )
    else:
        m = Map(location=[center_lat, center_lon], zoom_start=7, tiles="OpenStreetMap")

    # Show markers or heatmap based on user choice
    if map_view_mode == "markers":
        dtn_cluster = MarkerCluster(name="DTN Defects", disableClusteringAtZoom=13).add_to(m)
        tec_cluster = MarkerCluster(name="ATGMS Defects", disableClusteringAtZoom=13).add_to(m)

        # Add DTN markers
        if {'Latitude', 'Longitude'}.issubset(dtn_df.columns):
            for _, row in dtn_df.dropna(subset=['Latitude', 'Longitude']).iterrows():
                popup_html = create_popup_html(row, "DTN")
                Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=folium.Popup(popup_html, max_width=400),
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(dtn_cluster)

        # Add TEC markers
        if {'Latitude', 'Longitude'}.issubset(tec_df.columns):
            for _, row in tec_df.dropna(subset=['Latitude', 'Longitude']).iterrows():
                popup_html = create_popup_html(row, "TEC")
                Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=folium.Popup(popup_html, max_width=400),
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(tec_cluster)
    else:
        # Create a heatmap with combined coordinates
        heat_data = process_coordinates(dtn_df) + process_coordinates(tec_df)
        if heat_data:
            HeatMap(heat_data).add_to(m)

    # Add the locate control to find your position on the map
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
    # Filter the DataFrame based on user selections
    for column, value in filters.items():
        if value != "All" and column in df.columns:
            df = df[df[column] == value]
    return df

def create_sidebar_filters(df, prefix, filter_columns, default_values=None):
    # Create a select box for each filterable column in the sidebar
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
    # Put the most important columns first in the DataFrame
    available_cols = [col for col in priority_columns if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in priority_columns]
    return df[available_cols + remaining_cols]

def main():
    # Set page width and title
    st.set_page_config(layout="wide", page_title="Defect.ODN")
    st.title("Curated DTN and ATGMS Defect Dashboard")

    # Initialize a session state variable for live tracking
    if "live_tracking" not in st.session_state:
        st.session_state["live_tracking"] = False

    # Load the data
    dtn_df, tec_df = load_data()
    if dtn_df is None or tec_df is None:
        return

    # Let the user pick a subdivision
    subdivision_choice = st.selectbox("Select a Subdivision to View:", SUBDIVISIONS)

    # Filter the data by the chosen subdivision
    if "Subdivision" in dtn_df.columns and "Subdivision" in tec_df.columns:
        filtered_dtn_df = dtn_df[dtn_df["Subdivision"] == subdivision_choice]
        filtered_tec_df = tec_df[tec_df["Subdivision"] == subdivision_choice]
    else:
        st.error("Error: 'Subdivision' column not found in one or both datasets.")
        return

    # Add sidebar filters
    st.sidebar.header("Filter Options")

    # Default filter options for both DataFrames
    dtn_default_filters = {
        "Status": "Open"
    }
    tec_default_filters = {
        "Status": "Confirmed",
        "Sys": "TGMS",
        "Severity": "Urgent"
    }

    # Create filter widgets for DTN
    st.sidebar.subheader("DTN Filters")
    dtn_filters = create_sidebar_filters(
        filtered_dtn_df,
        "DTN",
        ["Status", "Asset"],
        default_values=dtn_default_filters
    )
    filtered_dtn_df = filter_dataframe(filtered_dtn_df, dtn_filters)

    # Create filter widgets for TEC
    st.sidebar.subheader("TEC Filters")
    tec_filters = create_sidebar_filters(
        filtered_tec_df,
        "TEC",
        ["Status", "Sys", "Severity"],
        default_values=tec_default_filters
    )
    filtered_tec_df = filter_dataframe(filtered_tec_df, tec_filters)

    # Make sure certain columns come first
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

    # Different basemap options for the user to pick from
    basemap_options = {
        "Street (OpenStreetMap)": "OpenStreetMap",
        "Light (CartoDB positron)": "CartoDB positron",
        "Dark (CartoDB dark_matter)": "CartoDB dark_matter",
        "Topographic (OpenTopoMap)": "OpenTopoMap",
        "ESRI World Street Map": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
            "attribution": "Tiles &copy; Esri — Source: Esri, DeLorme, NAVTEQ, USGS, etc."
        },
        "ESRI World Topo Map": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
            "attribution": "Tiles &copy; Esri — Source: Esri, DeLorme, NAVTEQ, USGS, etc."
        },
        "ESRI World Imagery": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attribution": "Tiles &copy; Esri, i-cubed, USDA, USGS, AEX, GeoEye, etc."
        }
    }

    # Pick how the map should look and which basemap to use
    st.sidebar.markdown("---")
    st.sidebar.subheader("Map Settings")

    map_view_mode = st.sidebar.radio(
        "Select Map View",
        ("markers", "heatmap"),
        format_func=lambda x: "Scatter Plot (Markers)" if x == "markers" else "Heatmap"
    )

    basemap_choice = st.sidebar.selectbox(
        "Select Basemap Style",
        list(basemap_options.keys()),
        index=0
    )

    # Live tracking buttons
    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("Start Live Tracking"):
            st.session_state["live_tracking"] = True
    with col2:
        if st.button("Stop Live Tracking"):
            st.session_state["live_tracking"] = False

    # Reset all filters
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Filters"):
        st.experimental_rerun()

    # Show the map in an expander
    with st.expander("Map Visualization", expanded=True):
        if {'Latitude', 'Longitude'}.issubset(rearranged_dtn_df.columns) or \
                {'Latitude', 'Longitude'}.issubset(rearranged_tec_df.columns):
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

            # Create and show the Folium map
            map_obj = create_map(
                rearranged_dtn_df,
                rearranged_tec_df,
                map_view_mode,
                basemap_options[basemap_choice]
            )
            folium_static(map_obj, width=1600, height=600)

            # Tips on location permission
            st.markdown(
                "**Note**: If you do not see your location on the map, make sure to allow location "
                "permissions in your browser and that you are running this app over HTTPS or localhost."
            )
        else:
            st.warning("No coordinate data available for mapping.")

    # Display the data tables
    st.header(f"Filtered Data for Subdivision: {subdivision_choice}")

    st.subheader("DTN Defects Filtered")
    st.markdown(f"**Total Rows: {len(rearranged_dtn_df)}**")
    st.dataframe(rearranged_dtn_df)

    st.subheader("ATGMS Defects Filtered")
    st.markdown(f"**Total Rows: {len(rearranged_tec_df)}**")
    st.dataframe(rearranged_tec_df)

if __name__ == "__main__":
    main()
