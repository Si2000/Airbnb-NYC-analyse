import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Dashboard Airbnb en Metro in NYC", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_csv("NYC_Airbnb_Subway_Final.csv", parse_dates=["last_review"])
    mta_map = pd.read_csv("MTA_Subway_Stations_map.csv")
    return df, mta_map


df, mta_map = load_data()

st.title("Dashboard Airbnb en Metro in New York City")

# Sidebar filters
st.sidebar.header("Filters")

boroughs = st.sidebar.multiselect(
    "Stadsdeel",
    sorted(df["neighbourhood_group"].dropna().unique()),
    default=sorted(df["neighbourhood_group"].dropna().unique())
)

room_types = st.sidebar.multiselect(
    "Type kamer",
    sorted(df["room_type"].dropna().unique()),
    default=sorted(df["room_type"].dropna().unique())
)

filtered_df = df[
    df["neighbourhood_group"].isin(boroughs) &
    df["room_type"].isin(room_types)
].copy()

tab1, tab2, tab3, tab4 = st.tabs(["Overzicht", "Prijsanalyse", "Kaartweergave", "Prijsadviseur"])

with tab1:
    st.markdown("# Overzicht")
    st.markdown("---")

    st.markdown("## Voorbeeld van de data")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.dataframe(filtered_df.head(8), use_container_width=True)

    with col_b:
        st.markdown("### Samenvatting van de dataset")
        st.write(f"**Aantal rijen:** {filtered_df.shape[0]:,}")
        st.write(f"**Aantal kolommen:** {filtered_df.shape[1]}")
        st.write(f"**Unieke stadsdelen:** {filtered_df['neighbourhood_group'].nunique()}")
        st.write(f"**Unieke kamertypes:** {filtered_df['room_type'].nunique()}")

    st.markdown("### Datacleaning")
    st.markdown(
        """
        - Ontbrekende waarden in **name** en **host_name** zijn ingevuld met `"Onbekend"`.
        - Ontbrekende waarden in **reviews_per_month** zijn ingevuld met `0`.
        - Ontbrekende waarden in **last_review** zijn behouden, omdat dit waarschijnlijk betekent dat een listing nog geen reviews heeft.
        - Listings met **price = 0** zijn verwijderd.
        - Extreme uitschieters(>=500) in **price** zijn weggefilterd.
        - Onrealistische waarden in **minimum_nights** zijn verwijderd.
        """
    )

    st.markdown("---")

    st.markdown("## Overzicht van feature engineering")


    st.markdown(
            """
            ### Nieuwe kenmerken
            - **price_level_in_hood**: Relatief prijsniveau binnen de buurt
            - **nearest_station_distance_km**: Afstand tot het dichtstbijzijnde metrostation
            - **nearest_station**: Naam van het dichtstbijzijnde metrostation
            - **distance_category**: Afstand gegroepeerd in loopcategorieën
            - **nearest_station_route_count**: Aantal metrolijnen overdag bij het dichtstbijzijnde station
            """
    )

    feature_cols = [
        "price",
        "price_level_in_hood",
        "nearest_station_distance_km",
        "nearest_station",
        "nearest_station_route_count",
        "distance_category"
    ]

    st.dataframe(filtered_df[feature_cols].head(8), use_container_width=True)


with tab2:
    st.subheader("Prijsanalyse")


#### 1e plot
    distance_order = ["0-250m", "250-500m", "500-1000m", "1-2km", ">2km"]

    fig_box = px.box(
        filtered_df,
        x="distance_category",
        y="price",
        color="distance_category",
        category_orders={"distance_category": distance_order},
        labels={
        "distance_category_nl": "Afstandscategorie",
        "price": "Prijs"
        },
        title="Prijs per afstandscategorie"
    )

    fig_box.update_layout(
        xaxis_title="Afstandscategorie",
        yaxis_title="Prijs"
    )

    st.plotly_chart(fig_box, use_container_width=True)


#### 2e plot
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
        labels={
        "neighbourhood_group_nl": "Stadsdeel",
        "price": "Mediaanprijs",
        "room_type_nl": "Kamertype"
        },
        title="Mediaanprijs per stadsdeel en kamertype"
    )

    fig_grouped.update_layout(
        xaxis_title="Stadsdeel",
        yaxis_title="Mediaanprijs",
        legend_title="Type kamer"
    )

    st.plotly_chart(fig_grouped, use_container_width=True)

#### 3e plot

    route_price = (
        filtered_df.groupby("nearest_station_route_count", as_index=False)["price"]
        .median()
        .sort_values("nearest_station_route_count")
    )

    fig_line_routes = px.line(
        route_price,
        x="nearest_station_route_count",
        y="price",
        title="Mediaanprijs per aantal metrolijnen",
        labels={
            "nearest_station_route_count": "Aantal metrolijnen in de buurt",
            "price": "Mediaanprijs"
        },
        markers=True
    )

    fig_line_routes.update_xaxes(dtick=1)

    st.plotly_chart(fig_line_routes, use_container_width=True)


#### 4e plot

    host_df = filtered_df[
        filtered_df["calculated_host_listings_count"].notna() &
        filtered_df["price"].notna()
    ].copy()


    def classify_host(count):
        if count == 1:
            return "1 advertentie"
        elif 2 <= count <= 5:
            return "2-5 advertenties"
        elif 6 <= count <= 10:
            return "6-10 advertenties"
        elif 11 <= count <= 20:
            return "11-20 advertenties"
        else:
            return "21+ advertenties"


    # Nieuwe kolom maken met hostgroepen
    host_df["host_listing_group"] = host_df["calculated_host_listings_count"].apply(classify_host)

    group_order = [
        "1 advertentie",
        "2-5 advertenties",
        "6-10 advertenties",
        "11-20 advertenties",
        "21+ advertenties"
    ]

    fig_host_box = px.box(
        host_df,
        x="host_listing_group",
        y="price",
        color="host_listing_group",
        title="Prijsverdeling per type host",
        category_orders={"host_listing_group": group_order},
        labels={
            "host_listing_group": "Type host",
            "price": "Prijs"
        },
        points="outliers"
    )

    fig_host_box.update_layout(
        xaxis_title="Type host",
        yaxis_title="Prijs",
        showlegend=False
    )

    st.plotly_chart(fig_host_box, use_container_width=True)





with tab3:
    st.markdown("# Kaartweergave")
    st.markdown("---")

    @st.cache_data
    def prepare_station_data(mta_map):
        station_df = mta_map[
            mta_map["GTFS Latitude"].notna() &
            mta_map["GTFS Longitude"].notna()
        ].copy()

        station_df = station_df.rename(columns={
            "GTFS Latitude": "lat",
            "GTFS Longitude": "lon"
        })

        return station_df


### STADSDEEL SELECTBOX
    borough_options = sorted(filtered_df["neighbourhood_group"].dropna().unique().tolist())
    borough_select_options = ["Alle stadsdelen"] + borough_options

    default_borough = "Manhattan" if "Manhattan" in borough_options else "Alle stadsdelen"

    selected_borough = st.selectbox(
        "Kies een stadsdeel",
        options=borough_select_options,
        index=borough_select_options.index(default_borough)
    )

    if selected_borough == "Alle stadsdelen":
        borough_df = filtered_df
    else:
        borough_df = filtered_df[
            filtered_df["neighbourhood_group"] == selected_borough
        ]


### BUURT SELECTBOX

    neighbourhood_options = sorted(borough_df["neighbourhood"].dropna().unique().tolist())
    default_hood = neighbourhood_options[0] if neighbourhood_options else None

    selected_neighbourhoods = st.multiselect(
        "Kies één of meer buurten",
        options=neighbourhood_options,
        default=[default_hood] if default_hood and selected_borough != "Alle stadsdelen" else []
    )

    if selected_neighbourhoods:
        map_df = borough_df[
            borough_df["neighbourhood"].isin(selected_neighbourhoods)
        ]
    else:
        map_df = borough_df

    if map_df.empty:
        st.warning("Er is geen data beschikbaar voor de gekozen filters.")
        st.stop()

    valid_map_df = map_df[
        map_df["latitude"].notna() &
        map_df["longitude"].notna() &
        map_df["price"].notna()
    ]

    if valid_map_df.empty:
        st.warning("Er zijn geen geldige coördinaten beschikbaar voor deze selectie.")
        st.stop()


#### COLUMN
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        show_all_points = st.checkbox("Toon alle Airbnb-punten", value=False)

    with col_b:
        show_popup = st.checkbox("Toon popup-info", value=False)

    with col_c:
        show_subway_stations = st.checkbox("Toon metrostations", value=False)

    if show_all_points:
        sample_df = valid_map_df.copy()
        if len(sample_df) > 3000:
            st.warning("Het tonen van alle punten kan de kaart trager maken.")
    else:
        max_points = len(valid_map_df)

        sample_size = st.slider(
            "Aantal Airbnb-punten op de kaart",
            min_value=1,
            max_value=max_points,
            value=min(500, max_points),
            step=100 if max_points >= 100 else 1
        )

        if len(valid_map_df) > sample_size:
            sample_df = valid_map_df.sample(sample_size, random_state=42)
        else:
            sample_df = valid_map_df.copy()



### map maken
    center_lat = sample_df["latitude"].mean()
    center_lon = sample_df["longitude"].mean()

    zoom_level = 10 if selected_borough == "Alle stadsdelen" else 13

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles="CartoDB positron"
    )


### airbnb punt
    def get_price_color(price):
        if price < 50:
            return "green"
        elif price < 100:
            return "blue"
        elif price < 200:
            return "yellow"
        elif price < 400:
            return "red"
        else:
            return "darkred"

    for row in sample_df.itertuples():
        price_value = row.price
        marker_color = get_price_color(price_value)

        popup_text = None
        if show_popup:
            popup_text = f"""
            <b>Prijs:</b> ${price_value}<br>
            <b>Buurt:</b> {row.neighbourhood}<br>
            <b>Kamertype:</b> {row.room_type}
            """

        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=2,
            color=marker_color,
            weight=0.5,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=popup_text
        ).add_to(m)


#### legend op map
    legend_html = """
    <div style="
        position: fixed;
        bottom: 40px;
        left: 40px;
        width: 190px;
        background-color: white;
        border: 2px solid grey;
        z-index: 9999;
        font-size: 14px;
        padding: 10px;
        border-radius: 6px;
    ">
        <b>Prijs per nacht</b><br>
        <i style="background:green;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> Minder dan 50<br>
        <i style="background:blue;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> 50 - 100<br>
        <i style="background:yellow;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> 100 - 200<br>
        <i style="background:red;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> 200 - 400<br>
        <i style="background:darkred;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> Meer dan 400
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


### metropunt
    if show_subway_stations:
        station_df = prepare_station_data(mta_map)

        lat_min = sample_df["latitude"].min() - 0.02
        lat_max = sample_df["latitude"].max() + 0.02
        lon_min = sample_df["longitude"].min() - 0.02
        lon_max = sample_df["longitude"].max() + 0.02

        station_df = station_df[
            (station_df["lat"] >= lat_min) &
            (station_df["lat"] <= lat_max) &
            (station_df["lon"] >= lon_min) &
            (station_df["lon"] <= lon_max)
        ].copy()



        for row in station_df.itertuples():
            folium.CircleMarker(
                location=[row.lat, row.lon],
                radius=4,
                color="black",       
                weight=2,
                fill=True,
                fill_color="white",  
                fill_opacity=1
            ).add_to(m)

    st_folium(m, width=1400, height=750)




with tab4:
    st.markdown("# Prijschecker voor gasten")
    st.markdown("---")

    distance_order = ["0-250m", "250-500m", "500-1000m", "1-2km", ">2km"]


### select box
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        adviser_borough = st.selectbox(
            "Kies een stadsdeel",
            sorted(df["neighbourhood_group"].dropna().unique()),
            key="adviser_borough"
        )

    with col2:
        adviser_neighbourhood_options = sorted(
            df[df["neighbourhood_group"] == adviser_borough]["neighbourhood"].dropna().unique()
        )

        adviser_neighbourhood = st.selectbox(
            "Kies een buurt",
            adviser_neighbourhood_options,
            key="adviser_neighbourhood"
        )

    with col3:
        adviser_room_type = st.selectbox(
            "Kies een kamertype",
            sorted(df["room_type"].dropna().unique()),
            key="adviser_room_type"
        )

    with col4:
        adviser_distance = st.selectbox(
            "Afstand tot metrostation",
            distance_order,
            key="adviser_distance"
        )

    exact_df = df[
        (df["neighbourhood_group"] == adviser_borough) &
        (df["neighbourhood"] == adviser_neighbourhood) &
        (df["room_type"] == adviser_room_type) &
        (df["distance_category"] == adviser_distance)
    ]

    used_level = "buurt + kamertype + afstand tot metro"


### wat gebeurt als er geen genoeg data
    if len(exact_df) >= 10:
        comparable_df = exact_df
    else:
        broader_df_1 = df[
            (df["neighbourhood_group"] == adviser_borough) &
            (df["neighbourhood"] == adviser_neighbourhood) &
            (df["room_type"] == adviser_room_type)
        ]

        if len(broader_df_1) >= 10:
            comparable_df = broader_df_1
            used_level = "buurt + kamertype"
        else:
            broader_df_2 = df[
                (df["neighbourhood_group"] == adviser_borough) &
                (df["room_type"] == adviser_room_type)
            ]

            comparable_df = broader_df_2
            used_level = "stadsdeel + kamertype"

    comparable_df = comparable_df[comparable_df["price"].notna()]



### conclusie
    if comparable_df.empty:
        st.warning("Er is niet genoeg data beschikbaar om een prijsinschatting te geven.")
    else:
        q25 = comparable_df["price"].quantile(0.25)
        median_price = comparable_df["price"].median()
        q75 = comparable_df["price"].quantile(0.75)
        mean_price = comparable_df["price"].mean()
        n_listings = len(comparable_df)
        exact_count = len(exact_df)

        st.markdown("## Verwachte prijsrange")

        c1, c2 = st.columns(2)
        with c1:
            st.success(f"Normale prijsrange: \\${q25:.0f} - \\${q75:.0f} per nacht")
        with c2:
            st.info(f"Typische prijs: \\${median_price:.0f} per nacht")


        st.markdown("## Vergelijkbare Airbnb")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Aantal vergelijkbare accommodaties", n_listings)
        with m2:
            st.metric("Gemiddelde prijs", f"${mean_price:.0f}")
        with m3:
            st.metric("Typische prijs", f"${median_price:.0f}")
        with m4:
            st.metric("Exacte matches", exact_count)