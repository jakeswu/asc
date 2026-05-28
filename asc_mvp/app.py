import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components

st.set_page_config(page_title="WA ASC Intelligence", layout="wide")

st.title("WA ASC Intelligence")
st.caption("Helping you spot patterns and unmet needs")

components.html(
    """
    <script data-goatcounter="https://ascwastate.goatcounter.com/count"
            async src="https://gc.zgo.at/count.js"></script>
    """,
    height=0,
)

# ── Census population fetch ───────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_wa_county_population():
    """
    Pull ACS 5-year county population estimates for Washington State.
    Returns a DataFrame with County (clean name), FIPS, Population.
    No API key required for this endpoint.
    """
    url = (
        "https://api.census.gov/data/2022/acs/acs5"
        "?get=NAME,B01003_001E"
        "&for=county:*"
        "&in=state:53"  # 53 = Washington
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        headers = data[0]
        rows = data[1:]
        pop_df = pd.DataFrame(rows, columns=headers)
        pop_df = pop_df.rename(columns={"B01003_001E": "Population", "NAME": "County_Full"})
        pop_df["Population"] = pd.to_numeric(pop_df["Population"], errors="coerce")
        # Strip " County, Washington" suffix
        pop_df["County"] = pop_df["County_Full"].str.replace(r" County, Washington", "", regex=True)
        pop_df["FIPS"] = pop_df["state"] + pop_df["county"]
        return pop_df[["County", "FIPS", "Population"]]
    except Exception as e:
        st.warning(f"Could not fetch Census data: {e}. White space analysis unavailable.")
        return pd.DataFrame(columns=["County", "FIPS", "Population"])


# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("asc_mvp/ascs.csv")
coords = pd.read_csv("asc_mvp/city_coordinates.csv")
movements_df = pd.read_csv("asc_mvp/movements.csv")
pop_df = fetch_wa_county_population()

# ── Sidebar filters ───────────────────────────────────────────────────────────
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

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered_df = df[
    df["City"].isin(selected_cities)
    & df["OwnerType"].isin(selected_owner_types)
    & df["Owner"].isin(selected_owners)
    & df["Operator"].isin(selected_operators)
    & df["Specialty"].isin(selected_specialties)
    & df["Region"].isin(selected_regions)
]

# ── Top metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("ASCs Shown", len(filtered_df))
col2.metric("Total ASCs", len(df))
col3.metric("Cities Shown", filtered_df["City"].nunique())
col4.metric("Specialties Shown", filtered_df["Specialty"].nunique())

# ── White Space Analysis ──────────────────────────────────────────────────────
st.header("🔍 White Space Analysis — ASC Density by County")
st.caption("Counties ranked by ASCs per 100,000 residents. Lower = underserved relative to population.")

if not pop_df.empty and "County" in df.columns:
    # Count ASCs per county from full (unfiltered) dataset
    county_asc_counts = (
        df.groupby("County")
        .agg(ASC_Count=("Name", "count"))
        .reset_index()
    )

    # Merge with population
    county_analysis = pop_df.merge(county_asc_counts, on="County", how="left")
    county_analysis["ASC_Count"] = county_analysis["ASC_Count"].fillna(0).astype(int)
    county_analysis["ASCs_per_100k"] = (
        (county_analysis["ASC_Count"] / county_analysis["Population"]) * 100000
    ).round(2)

    # State average for reference line
    state_avg = (df.shape[0] / pop_df["Population"].sum()) * 100000

    # Sort: zero-ASC counties first, then lowest density
    county_analysis = county_analysis.sort_values(
        by=["ASC_Count", "ASCs_per_100k"], ascending=[True, True]
    )

    # Insight callout — top 3 underserved counties with population > 50k
    underserved = county_analysis[
        (county_analysis["Population"] > 50000) & (county_analysis["ASCs_per_100k"] < state_avg)
    ].head(3)

    if not underserved.empty:
        st.info(
            "**Top underserved markets (population >50k, below state average density):** "
            + " · ".join(
                f"{row.County} ({row.ASC_Count} ASCs, {row.Population:,.0f} people)"
                for row in underserved.itertuples()
            )
        )

    # Bar chart — all counties
    ws_fig = px.bar(
        county_analysis,
        x="County",
        y="ASCs_per_100k",
        color="ASCs_per_100k",
        color_continuous_scale="RdYlGn",
        hover_data={"ASC_Count": True, "Population": ":,"},
        labels={"ASCs_per_100k": "ASCs per 100k residents"},
        height=450,
    )
    ws_fig.add_hline(
        y=state_avg,
        line_dash="dash",
        line_color="steelblue",
        annotation_text=f"State avg: {state_avg:.2f}",
        annotation_position="top right",
    )
    ws_fig.update_layout(
        xaxis_tickangle=-45,
        margin={"r": 0, "t": 20, "l": 0, "b": 120},
        coloraxis_showscale=False,
    )
    st.plotly_chart(ws_fig, use_container_width=True)

    # White space table
    with st.expander("Full county density table"):
        st.dataframe(
            county_analysis[["County", "Population", "ASC_Count", "ASCs_per_100k"]]
            .sort_values("ASCs_per_100k"),
            use_container_width=True,
        )
else:
    st.info(
        "White space analysis requires a **County** column in your ASC data and a live Census connection. "
        "Add a County column to ascs.csv to enable this section."
    )

# ── Map ───────────────────────────────────────────────────────────────────────
st.header("ASC Concentration by City")

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
    fig.update_traces(marker=dict(opacity=0.9, sizemin=8))
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
else:
    st.info("No map data available for the current filters.")

# ── Specialty distribution ────────────────────────────────────────────────────
st.header("ASC Specialty Distribution")

specialty_counts = filtered_df["Specialty"].value_counts().reset_index()
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

# ── Specialty × Region heatmap ────────────────────────────────────────────────
st.header("Specialty Coverage by Region")
st.caption("How many ASCs offer each specialty, broken down by region. Blank = none present.")

pivot = (
    filtered_df.groupby(["Region", "Specialty"])
    .size()
    .reset_index(name="Count")
    .pivot(index="Region", columns="Specialty", values="Count")
    .fillna(0)
    .astype(int)
)

if not pivot.empty:
    heat_fig = px.imshow(
        pivot,
        color_continuous_scale="Blues",
        aspect="auto",
        labels={"color": "ASC Count"},
        height=400,
    )
    heat_fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0})
    st.plotly_chart(heat_fig, use_container_width=True)

# ── Operator leaderboard ──────────────────────────────────────────────────────
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

# ── Market movements ──────────────────────────────────────────────────────────
st.header("Recent ASC Market Movements")

if not movements_df.empty:
    movements_df = movements_df.sort_values(by="Date", ascending=False)
    st.dataframe(movements_df, use_container_width=True)
else:
    st.info("No market movements tracked yet.")

# ── Raw registry ──────────────────────────────────────────────────────────────
st.header("ASC Registry")
st.write(f"Showing {len(filtered_df)} of {len(df)} ASCs")
st.dataframe(filtered_df, use_container_width=True)
