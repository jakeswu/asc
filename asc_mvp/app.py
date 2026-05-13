import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

st.set_page_config(page_title="WA ASC Intelligence", layout="wide")

st.title("WA ASC Intelligence")
st.caption("Helping you spot patterns and unmet needs")

import streamlit.components.v1 as components

components.html(
    """
    <script data-goatcounter="https://ascwastate.goatcounter.com/count"
            async src="https://gc.zgo.at/count.js"></script>
    """,
    height=0,
)

# Load data
df = pd.read_csv("asc_mvp/ascs.csv")

# Sidebar filters
st.sidebar.header("Filters")

city_options = sorted(df["City"].dropna().unique())
selected_cities = st.sidebar.multiselect("City", city_options, default=city_options)

owner_type_options = sorted(df["OwnerType"].dropna().unique())
selected_owner_types = st.sidebar.multiselect("OwnerType", owner_type_options, default=owner_type_options)

owner_options = sorted(df["Owner"].dropna().unique())
selected_owners = st.sidebar.multiselect("Owner", owner_options, default=owner_options)

operator_options = sorted(df["Operator"].dropna().unique())
selected_operators = st.sidebar.multiselect("Operator", operator_options, default=operator_options)

specialty_options = sorted(df["Specialty"].dropna().unique())
selected_specialties = st.sidebar.multiselect("Specialty", specialty_options, default=specialty_options)

region_options = sorted(df["Region"].dropna().unique())
selected_regions = st.sidebar.multiselect("Region", region_options, default=region_options)

# Apply filters
filtered_df = df[
    df["City"].isin(selected_cities)
    & df["OwnerType"].isin(selected_owner_types)
    & df["Owner"].isin(selected_owners)
    & df["Operator"].isin(selected_operators)
    & df["Specialty"].isin(selected_specialties)
    & df["Region"].isin(selected_regions)
]

# Top metrics
col1, col2, col3, col4 = st.columns(4)

col1.metric("ASCs Shown", len(filtered_df))
col2.metric("Total ASCs", len(df))
col3.metric("Cities Shown", filtered_df["City"].nunique())
col4.metric("Specialties Shown", filtered_df["Specialty"].nunique())

# Map
st.header("ASC Concentration by City")

coords = pd.read_csv("asc_mvp/city_coordinates.csv")
map_df = filtered_df.merge(coords, on="City", how="left")

city_summary = (
    map_df.dropna(subset=["Latitude", "Longitude"])
    .groupby(["City", "Region", "Latitude", "Longitude"])
    .agg(
        ASC_Count=("Name", "count"),
        Specialty_Mix=("Specialty", lambda x: ", ".join(sorted(set(x.dropna())))),
        ASC_Names=("Name", lambda x: "<br>".join(sorted(x.dropna()))),
    )
    .reset_index()
)

if not city_summary.empty:
    fig = px.scatter_mapbox(
        city_summary,
        lat="Latitude",
        lon="Longitude",
        size="ASC_Count",
        color="Region",
        hover_name="City",
        hover_data={
            "ASC_Count": True,
            "Specialty_Mix": True,
            "ASC_Names": True,
            "Latitude": False,
            "Longitude": False,
        },
        zoom=6,
        height=600,
        color_discrete_sequence=px.colors.qualitative.Bold,
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_center={"lat": 47.4, "lon": -120.7},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )

    fig.update_traces(
        marker=dict(
            opacity=0.9,
            sizemin=8,
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"scrollZoom": True},
    )
else:
    st.info("No map data available for the current filters.")

# Specialty distribution
st.header("ASC Specialty Distribution")

specialty_counts = (
    filtered_df["Specialty"]
    .value_counts()
    .reset_index()
)

specialty_counts.columns = ["Specialty", "ASC_Count"]

if not specialty_counts.empty:
    specialty_fig = px.bar(
        specialty_counts,
        x="Specialty",
        y="ASC_Count",
        color="Specialty",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )

    specialty_fig.update_layout(
        xaxis_title="Specialty",
        yaxis_title="ASC Count",
        showlegend=False,
        height=450,
        margin={"r": 0, "t": 20, "l": 0, "b": 0},
    )

    st.plotly_chart(specialty_fig, use_container_width=True)
else:
    st.info("No specialty data available for the current filters.")

# Operator leaderboard
st.header("Top ASC Owners / Operators")

operator_summary = (
    filtered_df.groupby("Owner")
    .agg(
        ASC_Count=("Name", "count"),
        Owner_Type=("OwnerType", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"),
        Primary_Specialty=("Specialty", lambda x: x.value_counts().idxmax() if not x.empty else "Unknown"),
        Regions=("Region", lambda x: ", ".join(sorted(set(x.dropna())))),
        Cities=("City", lambda x: ", ".join(sorted(set(x.dropna())))),
    )
    .reset_index()
    .sort_values(by="ASC_Count", ascending=False)
)

st.dataframe(operator_summary.head(25), use_container_width=True)
# Recent market movements
st.header("Recent ASC Market Movements")

movements_df = pd.read_csv("asc_mvp/movements.csv")

if not movements_df.empty:

    movements_df = movements_df.sort_values(
        by="Date",
        ascending=False
    )

    st.dataframe(
        movements_df,
        use_container_width=True
    )

else:
    st.info("No market movements tracked yet.")
# Raw table
st.header("ASC Registry")

st.write(f"Showing {len(filtered_df)} of {len(df)} ASCs")

st.dataframe(filtered_df, use_container_width=True)
