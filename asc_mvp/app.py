import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import folium
import requests
from streamlit_folium import st_folium

import requests as req

def track_pageview():
    try:
        r = req.get(
            "https://ascwastate.goatcounter.com/count",
            params={
                "p": "/",
                "t": "WA ASC Intelligence",
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://ascwastate.streamlit.app",
            },
            timeout=2,
        )
        st.write(r.status_code)
    except Exception as e:
        st.write(f"Error: {e}")

track_pageview()

st.set_page_config(page_title="WA ASC Intelligence", layout="wide")

st.title("WA ASC Intelligence")
st.caption("Helping you spot patterns and unmet needs")

# ── WA County Population (Census ACS 2022, baked in to avoid API dependency) ──
WA_COUNTY_POPULATION = {
    "Adams": 21040, "Asotin": 22582, "Benton": 204390, "Chelan": 79801,
    "Clallam": 77331, "Clark": 503478, "Columbia": 3985, "Cowlitz": 110593,
    "Douglas": 44734, "Ferry": 7627, "Franklin": 98592, "Garfield": 2225,
    "Grant": 99546, "Grays Harbor": 75379, "Island": 87038, "Jefferson": 34499,
    "King": 2269675, "Kitsap": 284320, "Kittitas": 47935, "Klickitat": 23149,
    "Lewis": 84141, "Lincoln": 10939, "Mason": 67798, "Okanogan": 43029,
    "Pacific": 23066, "Pend Oreille": 13943, "Pierce": 921130, "San Juan": 17582,
    "Skagit": 131062, "Skamania": 12083, "Snohomish": 857837, "Spokane": 536704,
    "Stevens": 46680, "Thurston": 299418, "Wahkiakum": 4488, "Walla Walla": 62977,
    "Whatcom": 240653, "Whitman": 50541, "Yakima": 257000,
}

pop_df = pd.DataFrame([
    {"County": k, "Population": v} for k, v in WA_COUNTY_POPULATION.items()
])

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("asc_mvp/ascs.csv")
coords = pd.read_csv("asc_mvp/city_coordinates.csv")
movements_df = pd.read_csv("asc_mvp/movements.csv")
city_county = pd.read_csv("asc_mvp/city_to_county.csv")
df = df.merge(city_county, on="City", how="left")

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

county_asc_counts = (
    df.groupby("County")
    .agg(ASC_Count=("Name", "count"))
    .reset_index()
)

county_analysis = pop_df.merge(county_asc_counts, on="County", how="left")
county_analysis["ASC_Count"] = county_analysis["ASC_Count"].fillna(0).astype(int)
county_analysis["ASCs_per_100k"] = (
    (county_analysis["ASC_Count"] / county_analysis["Population"]) * 100000
).round(2)

state_avg = (df.shape[0] / pop_df["Population"].sum()) * 100000

county_analysis = county_analysis.sort_values(
    by=["ASC_Count", "ASCs_per_100k"], ascending=[True, True]
)

# Insight callout
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

with st.expander("Full county density table"):
    st.dataframe(
        county_analysis[["County", "Population", "ASC_Count", "ASCs_per_100k"]]
        .sort_values("ASCs_per_100k"),
        use_container_width=True,
    )

# ── Map ───────────────────────────────────────────────────────────────────────
# ── Map ───────────────────────────────────────────────────────────────────────
st.header("ASC Concentration Map")

@st.cache_data(ttl=86400)
def load_wa_geojson():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    r = requests.get(url, timeout=10)
    all_counties = r.json()
    return {
        "type": "FeatureCollection",
        "features": [f for f in all_counties["features"] if f["id"].startswith("53")]
    }

wa_geojson = load_wa_geojson()

county_counts = (
    filtered_df.groupby("County")
    .agg(
        ASC_Count=("Name", "count"),
        Specialties=("Specialty", lambda x: ", ".join(sorted(set(x.dropna())))),
        ASC_Names=("Name", lambda x: "<br>• ".join(sorted(x.dropna()))),
    )
    .reset_index()
)

county_map_data = pop_df.merge(county_counts, on="County", how="left")
county_map_data["ASC_Count"] = county_map_data["ASC_Count"].fillna(0).astype(int)
county_map_data["ASCs_per_100k"] = (
    (county_map_data["ASC_Count"] / county_map_data["Population"]) * 100000
).round(2)
county_map_data["Specialties"] = county_map_data["Specialties"].fillna("None")
county_map_data["ASC_Names"] = county_map_data["ASC_Names"].fillna("None")

WA_COUNTY_FIPS = {
    "Adams": "53001", "Asotin": "53003", "Benton": "53005", "Chelan": "53007",
    "Clallam": "53009", "Clark": "53011", "Columbia": "53013", "Cowlitz": "53015",
    "Douglas": "53017", "Ferry": "53019", "Franklin": "53021", "Garfield": "53023",
    "Grant": "53025", "Grays Harbor": "53027", "Island": "53029", "Jefferson": "53031",
    "King": "53033", "Kitsap": "53035", "Kittitas": "53037", "Klickitat": "53039",
    "Lewis": "53041", "Lincoln": "53043", "Mason": "53045", "Okanogan": "53047",
    "Pacific": "53049", "Pend Oreille": "53051", "Pierce": "53053", "San Juan": "53055",
    "Skagit": "53057", "Skamania": "53059", "Snohomish": "53061", "Spokane": "53063",
    "Stevens": "53065", "Thurston": "53067", "Wahkiakum": "53069", "Walla Walla": "53071",
    "Whatcom": "53073", "Whitman": "53075", "Yakima": "53077",
}
county_map_data["FIPS"] = county_map_data["County"].map(WA_COUNTY_FIPS)

metric = st.radio("Color by", ["ASC Count", "ASCs per 100k"], horizontal=True)
metric_col = "ASC_Count" if metric == "ASC Count" else "ASCs_per_100k"

show_facilities = st.checkbox("Show existing ASC facilities", value=True)

m = folium.Map(location=[47.4, -120.7], zoom_start=7, tiles="CartoDB positron")

folium.Choropleth(
    geo_data=wa_geojson,
    name="choropleth",
    data=county_map_data,
    columns=["FIPS", metric_col],
    key_on="feature.id",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name=metric,
    nan_fill_color="lightgrey",
).add_to(m)

tooltip_data = county_map_data.set_index("FIPS")[
    ["County", "ASC_Count", "ASCs_per_100k", "Population", "Specialties", "ASC_Names"]
].to_dict(orient="index")

for feature in wa_geojson["features"]:
    fips = feature["id"]
    if fips in tooltip_data:
        d = tooltip_data[fips]
        folium.GeoJson(
            feature,
            style_function=lambda x: {"fillOpacity": 0, "weight": 0},
            tooltip=folium.Tooltip(
                f"<b>{d['County']} County</b><br>"
                f"ASCs: {d['ASC_Count']} | Density: {d['ASCs_per_100k']} per 100k<br>"
                f"Population: {d['Population']:,}"
            ),
            popup=folium.Popup(
                f"<b>{d['County']} County</b><br>"
                f"ASCs: {d['ASC_Count']} | Density: {d['ASCs_per_100k']} per 100k<br>"
                f"Population: {d['Population']:,}<br>"
                f"Specialties: {d['Specialties']}<br><br>"
                f"<b>Facilities:</b><br>• {d['ASC_Names']}",
                max_width=350,
            ),
        ).add_to(m)

if show_facilities:
    facility_df = filtered_df.merge(coords, on="City", how="left").dropna(subset=["Latitude", "Longitude"])
    
    city_groups = facility_df.groupby(["City", "Latitude", "Longitude"])
    
    for (city, lat, lon), group in city_groups:
        count = len(group)
        names = "<br>• ".join(sorted(group["Name"].dropna()))
        
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        background-color: steelblue;
                        color: white;
                        border-radius: 50%;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 11px;
                        font-weight: bold;
                        border: 2px solid white;
                        box-shadow: 1px 1px 3px rgba(0,0,0,0.3);
                    ">{count}</div>
                """,
                icon_size=(24, 24),
                icon_anchor=(12, 12),
            ),
            tooltip=folium.Tooltip(f"<b>{city}</b><br>{count} ASC{'s' if count > 1 else ''}"),
            popup=folium.Popup(
                f"<b>{city}</b> — {count} ASC{'s' if count > 1 else ''}<br><br>• {names}",
                max_width=300,
            ),
        ).add_to(m)

st_folium(m, width="100%", height=600, returned_objects=[])


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

# ── Specialty × Region heatmap ────────────────────────────────────────────────
st.header("Specialty Coverage by Region")
st.caption("How many ASCs offer each specialty per region. Blank = none present.")

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
