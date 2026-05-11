import streamlit as st
import pandas as pd

st.set_page_config(page_title="WA ASC Intelligence", layout="wide")

st.title("WA ASC Intelligence")

df = pd.read_csv("asc_mvp/data/ascs.csv")

st.sidebar.header("Filters")

city_options = sorted(df["City"].dropna().unique())
selected_cities = st.sidebar.multiselect("City", city_options, default=city_options)

owner_type_options = sorted(df["OwnerType"].dropna().unique())
selected_owner_types = st.sidebar.multiselect("OwnerType", owner_type_options, default=owner_type_options)

owner_options = sorted(df["Owner"].dropna().unique())
selected_owners = st.sidebar.multiselect("Owner", owner_options, default=owner_options)

operator_options = sorted(df["Operator"].dropna().unique())
selected_operators = st.sidebar.multiselect("Operator", operator_options, default=operator_options)

filtered_df = df[
    df["City"].isin(selected_cities)
    & df["OwnerType"].isin(selected_owner_types)
    & df["Owner"].isin(selected_owners)
    & df["Operator"].isin(selected_operators)
]

st.write(f"Showing {len(filtered_df)} of {len(df)} ASCs")

st.dataframe(filtered_df, use_container_width=True)
