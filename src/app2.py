import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import osmnx as ox
from utils import (
    geocode_location,
    haversine,
    find_closest_point,
    ruta_a_origen,
    ruta_a_destino,
    crear_ruta,
    add_route_line,
)
import networkx as nx


def main():
    valenbisi = pd.read_csv("data/valenbici_puntos.csv")
    valenbisi["geo_point_2d"] = valenbisi["geo_point_2d"].apply(lambda x: eval(x))

    preds = pd.read_parquet("data/valenbici_predictions_2025.parquet")

    preds["24h_time"] = preds[["Hour", "Minute"]].apply(
        lambda x: f"{x['Hour']:02d}:{x['Minute']:02d}", axis=1
    )
    preds["Date"] = preds[["Month", "Day"]].apply(
        lambda x: f"{x['Month']:02d}-{x['Day']:02d}", axis=1
    )

    possible_dates = preds["Date"].unique()

    coord_vb = set(valenbisi["geo_point_2d"].unique())
    G = ox.graph_from_point(
        (39.4699, -0.3763), dist=5000, network_type="bike", simplify=False
    )
    xs = [coord[1] for coord in coord_vb]
    ys = [coord[0] for coord in coord_vb]

    st.set_page_config(page_title="Valencia Bike Route Planner", layout="wide")
    st.title("🚲 Valencia Bike Route Planner")

    st.subheader("Select Route Details")
    col1, col2, col3 = st.columns(3)

    with col1:
        start_location = st.text_input(
            "Start Location", placeholder="e.g. Plaza del Ayuntamiento"
        )

    with col2:
        end_location = st.text_input(
            "End Location", placeholder="e.g. Ciudad de las Artes"
        )

    with col3:
        start_day = st.selectbox(
            "Start Date",
            options=possible_dates,
            format_func=lambda x: f"{x[:2]}-{x[3:]}",
            index=0,
        )
        start_time = st.time_input("Start Time")
        checker = st.button("Calculate Route")

    if checker:
        st.success(
            f"Planning route from **{start_location}** to **{end_location}** starting at **{start_time.strftime('%H:%M')}**"
        )

        start_hour = start_time.hour
        start_minute = start_time.minute

        filtered_preds = preds[
            (preds["Date"] == start_day)
            & (preds["Hour"] == start_hour)
            & (preds["Minute"] >= start_minute)
        ].nsmallest(273, "Minute")

        start_coords = geocode_location(start_location, "start")
        end_coords = geocode_location(end_location, "end")

        if start_coords:
            st.write(
                f"Start location coordinates: {start_coords.latitude}, {start_coords.longitude}"
            )
            resultados_start = ruta_a_origen(
                G, coord_vb, (start_coords.latitude, start_coords.longitude), xs, ys
            )

            for coord, distance in resultados_start:
                start_station = filtered_preds[
                    filtered_preds["geo_point_2d"].apply(
                        lambda x: (x[0], x[1]) == coord
                    )
                ].iloc[0]

                if start_station["bikes_pred_low"] > 1:
                    st.write(
                        f"Closest starting Valenbisi station: {start_station['Direccion']}"
                    )
                    est_origen = coord
                    break
        else:
            st.error("Could not find the start location. Please check the input.")

        if end_coords:
            st.write(
                f"End location coordinates: {end_coords.latitude}, {end_coords.longitude}"
            )
            resultados_end = ruta_a_destino(
                G, coord_vb, (end_coords.latitude, end_coords.longitude), xs, ys
            )
            for coord, distance in resultados_end:
                end_station = filtered_preds[
                    filtered_preds["geo_point_2d"].apply(
                        lambda x: (x[0], x[1]) == coord
                    )
                ].iloc[0]

                if end_station["bikes_pred_up"] < end_station["Espacios_totales"] - 1:
                    st.write(
                        f"Closest ending Valenbisi station: {end_station['Direccion']}"
                    )
                    est_destino = coord
                    break
        else:
            st.error("Could not find the end location. Please check the input.")

        if start_coords and end_coords:
            # pre_ruta, ruta, post_ruta = crear_ruta(
            #     G,
            #     coord_vb,
            #     (start_coords.latitude, start_coords.longitude),
            #     (end_coords.latitude, end_coords.longitude),
            #     xs,
            #     ys,
            # )

            origen_nodo = ox.nearest_nodes(
                G, start_coords.longitude, start_coords.latitude
            )
            destino_nodo = ox.nearest_nodes(
                G, end_coords.longitude, end_coords.latitude
            )

            est_origen_nodo = ox.nearest_nodes(G, est_origen[1], est_origen[0])
            est_destino_nodo = ox.nearest_nodes(G, est_destino[1], est_destino[0])

            pre_ruta = nx.shortest_path(
                G, origen_nodo, est_origen_nodo, weight="length"
            )
            ruta = nx.shortest_path(
                G, est_origen_nodo, est_destino_nodo, weight="length"
            )
            post_ruta = nx.shortest_path(
                G, est_destino_nodo, destino_nodo, weight="length"
            )

            st.subheader("Route Preview (placeholder)")
            m = folium.Map(location=[39.4699, -0.3763], zoom_start=13)
            folium.Marker(
                location=[start_coords.latitude, start_coords.longitude],
                popup=start_location,
                icon=folium.Icon(color="blue", icon="play", prefix="fa"),
            ).add_to(m)

            folium.Marker(
                location=[end_coords.latitude, end_coords.longitude],
                popup=end_location,
                icon=folium.Icon(color="red", icon="stop", prefix="fa"),
            ).add_to(m)

            folium.Marker(
                location=[
                    start_station["geo_point_2d"][0],
                    start_station["geo_point_2d"][1],
                    # start_station[0],
                    # start_station[1],
                ],
                popup=start_station["Direccion"],
                icon=folium.Icon(color="green", icon="bicycle", prefix="fa"),
            ).add_to(m)

            folium.Marker(
                location=[
                    end_station["geo_point_2d"][0],
                    end_station["geo_point_2d"][1],
                    # end_station[0],
                    # end_station[1],
                ],
                popup=end_station["Direccion"],
                icon=folium.Icon(color="orange", icon="bicycle", prefix="fa"),
            ).add_to(m)

            add_route_line(G, pre_ruta, "blue", m)
            add_route_line(G, ruta, "green", m)
            add_route_line(G, post_ruta, "red", m)

            col1, col2, col3 = st.columns([1, 6, 1])  # col2 será más ancho, centrado
            with col2:
                st_folium(m, use_container_width=True, height=500, returned_objects=[])
    else:
        st.info(
            "Please enter both start and end locations, time and click the button to view the route."
        )


if __name__ == "__main__":
    main()
