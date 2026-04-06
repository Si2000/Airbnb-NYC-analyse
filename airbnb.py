import streamlit as st
import pandas as pd
import plotly.express as px
import folium   
from streamlit_folium import st_folium
from branca.colormap import linear


st.set_page_config(page_title="NYC Airbnb & Subway Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("NYC_Airbnb_Subway_Final.csv", parse_dates=["last_review"])
    mta_map = pd.read_csv("MTA_Subway_Stations_map.csv")
    return df, mta_map

df, mta_map = load_data()

st.title("NYC Airbnb & Subway Dashboard")

# sidebar filters
st.sidebar.header("Filters")

boroughs = st.sidebar.multiselect(
    "Borough",
    sorted(df["neighbourhood_group"].dropna().unique()),
    default=sorted(df["neighbourhood_group"].dropna().unique())
)

room_types = st.sidebar.multiselect(
    "Room type",
    sorted(df["room_type"].dropna().unique()),
    default=sorted(df["room_type"].dropna().unique())
)

filtered_df = df[
    df["neighbourhood_group"].isin(boroughs) &
    df["room_type"].isin(room_types)
].copy()

tab1, tab2, tab3 = st.tabs(["Overview", "Price Analysis", "Map View"])

with tab1:
    st.markdown("# Overview")

    st.markdown("---")

    # =========================================================
    # 1. Data Preview
    # =========================================================
    st.markdown("## Data Preview")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.dataframe(filtered_df.head(8), use_container_width=True)

    with col_b:
        st.markdown("### Dataset Summary")
        st.write(f"**Rows:** {filtered_df.shape[0]:,}")
        st.write(f"**Columns:** {filtered_df.shape[1]}")
        st.write(f"**Unique boroughs:** {filtered_df['neighbourhood_group'].nunique()}")
        st.write(f"**Unique room types:** {filtered_df['room_type'].nunique()}")

    st.markdown("### Data Cleaning")
    st.markdown(
        """
        - Missing values in **name** and **host_name** were filled with `"Unknown"`.
        - Missing values in **reviews_per_month** were filled with `0`.
        - Missing values in **last_review** were kept, because they likely indicate that a listing has no reviews.
        - Listings with **price = 0** were removed.
        - Extreme outliers in **price** were filtered out.
        - Unrealistic values in **minimum_nights** were removed.
        - Coordinates were checked and confirmed to be within New York City.
        - Subway station data was reduced to the most relevant columns and checked for duplicates and missing values.
        """
    )

    st.markdown("---")

    # =========================================================
    # 2. Feature Engineering
    # =========================================================
    st.markdown("## Feature Engineering Overview")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(
            """
            ### New Features
            - **price_level_in_hood**: Relative price level within each neighborhood
            - **nearest_station_distance_km**: Distance to the nearest subway station
            - **nearest_station**: Name of the nearest subway station
            - **distance_category**: Distance grouped into walkability categories
            """
        )

    with col_right:
        st.markdown(
            """
            ### Extra Dimensions
            - **nearest_station_borough**: Borough of the nearest subway station
            - **nearest_station_ada**: Accessibility level of the nearest station
            - **nearest_station_route_count**: Number of daytime subway routes at the nearest station
            - **nearest_station_complex_id**: Station complex identifier
            """
        )

    feature_cols = [
        "price",
        "neighbourhood_group",
        "room_type",
        "price_level_in_hood",
        "nearest_station_distance_km",
        "nearest_station",
        "nearest_station_borough",
        "nearest_station_ada",
        "nearest_station_route_count",
        "distance_category"
    ]

    st.dataframe(filtered_df[feature_cols].head(8), use_container_width=True)

    st.markdown("---")

    # =========================================================
    # 3. Correlation Matrix
    # =========================================================
    st.markdown("## Correlation Matrix")

    corr_df = filtered_df.copy()

    # encode a few categorical columns for simple correlation
    room_type_map = {
        "Entire home/apt": 3,
        "Private room": 2,
        "Shared room": 1
    }
    price_level_map = {
        "Low": 1,
        "Medium": 2,
        "High": 3
    }

    corr_df["room_type_num"] = corr_df["room_type"].map(room_type_map)
    corr_df["price_level_num"] = corr_df["price_level_in_hood"].map(price_level_map)

    numeric_cols = [
        "price",
        "minimum_nights",
        "number_of_reviews",
        "reviews_per_month",
        "calculated_host_listings_count",
        "availability_365",
        "nearest_station_distance_km",
        "nearest_station_route_count",
        "room_type_num",
        "price_level_num"
    ]

    corr_matrix = corr_df[numeric_cols].corr()


    fig_corr = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation Matrix"
    )
    st.plotly_chart(fig_corr, use_container_width=True)


with tab2:
    st.subheader("Price Analysis")

    distance_order = ["0-250m", "250-500m", "500-1000m", "1-2km", ">2km"]

    fig_box = px.box(
        filtered_df,
        x="distance_category",
        y="price",
        color="distance_category",
        category_orders={"distance_category": distance_order},
        title="Price by Distance Category"
    )
    
    st.plotly_chart(fig_box, use_container_width=True)

####

    borough_room_price = (
    filtered_df.groupby(["neighbourhood_group", "room_type"], as_index=False)["price"]
    .median()
    )

    fig_grouped = px.bar(
        borough_room_price,
        x="neighbourhood_group",
        y="price",
        color="room_type",
        barmode="group",
        title="Median Price by Borough and Room Type"
    )
    st.plotly_chart(fig_grouped, use_container_width=True)
#####
    route_price = (
        filtered_df.groupby("nearest_station_route_count", as_index=False)["price"]
        .mean()
        .sort_values("nearest_station_route_count")
    )

    fig_bar_routes = px.bar(
        route_price,
        x="nearest_station_route_count",
        y="price",
        title="Average Price by Number of Subway Routes",
        labels={
            "nearest_station_route_count": "Number of subway routes nearby",
            "price": "Average price"
        }
    )
    fig_bar_routes.update_xaxes(dtick=1)
    st.plotly_chart(fig_bar_routes, use_container_width=True)

#####
    host_df = filtered_df[
    filtered_df["calculated_host_listings_count"].notna() &
    filtered_df["price"].notna()
    ].copy()

    host_df = host_df[host_df["price"] < 500]

    def classify_host(count):
        if count == 1:
            return "1 listing"
        elif 2 <= count <= 5:
            return "2-5 listings"
        elif 6 <= count <= 10:
            return "6-10 listings"
        elif 11 <= count <= 20:
            return "11-20 listings"
        else:
            return "21+ listings"

    host_df["host_listing_group"] = host_df["calculated_host_listings_count"].apply(classify_host)

    group_order = ["1 listing", "2-5 listings", "6-10 listings", "11-20 listings", "21+ listings"]

    host_group_price = (
        host_df.groupby("host_listing_group", as_index=False)["price"]
        .mean()
    )

    host_group_price["host_listing_group"] = pd.Categorical(
        host_group_price["host_listing_group"],
        categories=group_order,
        ordered=True
    )

    host_group_price = host_group_price.sort_values("host_listing_group")

    fig_host_bar = px.bar(
        host_group_price,
        x="host_listing_group",
        y="price",
        color="host_listing_group",
        title="Average Price by Host Listing Group",
        labels={
            "host_listing_group": "Host listing group",
            "price": "Average price"
        }
    )

    st.plotly_chart(fig_host_bar, use_container_width=True)

with tab3:




    st.subheader("Map View")


    @st.cache_data
    def prepare_station_data(mta_map: pd.DataFrame) -> pd.DataFrame:
        return mta_map[
            mta_map["GTFS Latitude"].notna() &
            mta_map["GTFS Longitude"].notna()
        ].copy()


    # ----------------------------
    # 1. Filters
    # ----------------------------
    borough_options = sorted(filtered_df["neighbourhood_group"].dropna().unique().tolist())
    borough_select_options = ["All"] + borough_options

    default_borough = "Manhattan" if "Manhattan" in borough_options else "All"

    selected_borough = st.selectbox(
        "Select borough",
        options=borough_select_options,
        index=borough_select_options.index(default_borough)
    )

    if selected_borough == "All":
        borough_df = filtered_df.copy()
    else:
        borough_df = filtered_df[
            filtered_df["neighbourhood_group"] == selected_borough
        ].copy()

    neighbourhood_options = sorted(borough_df["neighbourhood"].dropna().unique().tolist())
    default_hood = neighbourhood_options[0] if neighbourhood_options else None

    selected_neighbourhoods = st.multiselect(
        "Select neighbourhood(s)",
        options=neighbourhood_options,
        default=[default_hood] if default_hood and selected_borough != "All" else []
    )

    if selected_neighbourhoods:
        map_df = borough_df[
            borough_df["neighbourhood"].isin(selected_neighbourhoods)
        ].copy()
    else:
        map_df = borough_df.copy()

    if map_df.empty:
        st.warning("No data available for the selected filters.")
        st.stop()

    # ----------------------------
    # 2. Point controls
    # ----------------------------
    valid_map_df = map_df[
        map_df["latitude"].notna() &
        map_df["longitude"].notna() &
        map_df["price"].notna()
    ].copy()

    if valid_map_df.empty:
        st.warning("No valid coordinates available for the selected filters.")
        st.stop()

    show_all_points = st.checkbox("Show all points", value=False)

    if show_all_points:
        sample_df = valid_map_df.copy()
        if len(sample_df) > 3000:
            st.warning("Showing all points may make the map slow.")
    else:
        max_points = len(valid_map_df)

        sample_size = st.slider(
            "Number of Airbnb points",
            min_value=0,
            max_value=max_points,
            value= 10,
            step=100 if max_points >= 100 else 1
        )

        if len(valid_map_df) > sample_size:
            sample_df = valid_map_df.sample(sample_size, random_state=42)
        else:
            sample_df = valid_map_df.copy()

    show_subway_stations = st.checkbox("Show subway stations", value=True)

    # ----------------------------
    # 3. Create map
    # ----------------------------
    center_lat = sample_df["latitude"].mean()
    center_lon = sample_df["longitude"].mean()

    zoom_level = 10 if selected_borough == "All" else 13

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles="CartoDB positron"
    )

    # ----------------------------
    # 4. Airbnb listing layer
    # ----------------------------
    listing_group = folium.FeatureGroup(name="Airbnb Listings", show=True)

    price_min = sample_df["price"].quantile(0.05)
    price_max = sample_df["price"].quantile(0.95)

    if price_min == price_max:
        price_min = sample_df["price"].min()
        price_max = sample_df["price"].max()

    if price_min == price_max:
        price_max = price_min + 1

    colormap = linear.YlOrRd_09.scale(price_min, price_max)
    colormap.caption = "Airbnb Price"

    for _, row in sample_df.iterrows():
        price_value = row["price"]
        clipped_price = min(max(price_value, price_min), price_max)
        marker_color = colormap(clipped_price)

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=2,
            color=marker_color,
            weight=0.5,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.65
        ).add_to(listing_group)

    listing_group.add_to(m)
    colormap.add_to(m)

    # ----------------------------
    # 5. Subway stations only
    # ----------------------------
    if show_subway_stations:
        station_df = prepare_station_data(mta_map)

        lat_min = sample_df["latitude"].min() - 0.02
        lat_max = sample_df["latitude"].max() + 0.02
        lon_min = sample_df["longitude"].min() - 0.02
        lon_max = sample_df["longitude"].max() + 0.02

        station_df = station_df[
            (station_df["GTFS Latitude"] >= lat_min) &
            (station_df["GTFS Latitude"] <= lat_max) &
            (station_df["GTFS Longitude"] >= lon_min) &
            (station_df["GTFS Longitude"] <= lon_max)
        ].copy()

        stations_group = folium.FeatureGroup(name="Subway Stations", show=True)

        for _, row in station_df.iterrows():
            folium.CircleMarker(
                location=[row["GTFS Latitude"], row["GTFS Longitude"]],
                radius=2,
                color="black",
                weight=0.5,
                fill=True,
                fill_color="yellow",
                fill_opacity=0.85
            ).add_to(stations_group)

        stations_group.add_to(m)

    # ----------------------------
    # 6. Layer control
    # ----------------------------
    folium.LayerControl(collapsed=False).add_to(m)

    # ----------------------------
    # 7. Show map
    # ----------------------------
    st_folium(m, width=1400, height=750)