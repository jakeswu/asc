import streamlit as st
import pandas as pd

st.set_page_config(page_title="WA ASC Intelligence", layout="wide")

st.title("WA ASC Intelligence")
st.caption("Helping you spot patterns and unmet needs")

df = pd.read_csv("asc_mvp/ascs.csv")

import plotly.express as px

coords = pd.read_csv("asc_mvp/city_coordinates.csv")
map_df = df.merge(coords, on="City", how="left")

city_summary = (
    map_df.dropna(subset=["Latitude", "Longitude"])
    .groupby(["City", "Region", "Latitude", "Longitude"])
    .agg(
        ASC_Count=("Name", "count"),
        Specialty_Mix=("Specialty", lambda x: ", ".join(sorted(set(x.dropna()))))
    )
    .reset_index()
)

st.header("ASC Concentration by City")

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
        "Latitude": False,
        "Longitude": False
    },
    zoom=5,
    height=600
)

fig.update_layout(mapbox_style="open-street-map")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

st.plotly_chart(fig, use_container_width=True)

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

filtered_df = df[
    df["City"].isin(selected_cities)
    & df["OwnerType"].isin(selected_owner_types)
    & df["Owner"].isin(selected_owners)
    & df["Operator"].isin(selected_operators)
    & df["Specialty"].isin(selected_specialties)
    & df["Region"].isin(selected_regions)
]

st.write(f"Showing {len(filtered_df)} of {len(df)} ASCs")

st.dataframe(filtered_df, use_container_width=True)
