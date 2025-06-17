import streamlit as st
import datetime
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pandas as pd
from math import radians, cos, sin, asin, sqrt


def geocode_location(location_name, key):
    if key not in st.session_state or st.session_state[key + "_name"] != location_name:
        geolocator = Nominatim(user_agent="valencia-bike-route-app")
        try:
            location = geolocator.geocode(location_name, exactly_one=True)
            if location:
                st.session_state[key] = location
                st.session_state[key + "_name"] = location_name
            else:
                st.session_state[key] = None
        except Exception as e:
            st.session_state[key] = None
            st.error(f"Error during geocoding '{location_name}': {e}")
    return st.session_state[key]


def haversine(coord1, coord2):
    """
    Calcula la distancia Haversine entre dos puntos (lat, lon).
    Devuelve distancia en kilómetros.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Convertir a radianes
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Diferencias
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Fórmula Haversine
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    R = 6371  # Radio de la Tierra en km
    return R * c


def find_closest_point(df, target_coord, coord_col="geo_point_2d"):
    """
    Dado un DataFrame con una columna de tuplas (lat, lon) y una coordenada objetivo,
    devuelve la fila más cercana.
    """
    if coord_col not in df.columns:
        raise ValueError(f"La columna '{coord_col}' no está en el DataFrame.")

    if not isinstance(target_coord, tuple) or len(target_coord) != 2:
        raise ValueError("La coordenada objetivo debe ser una tupla (lat, lon).")

    distances = df[coord_col].apply(lambda x: haversine(x, target_coord))
    closest_idx = distances.idxmin()
    return df.loc[closest_idx]


def main():
    valenbisi = pd.read_csv("data/valenbici_puntos.csv")
    valenbisi["geo_point_2d"] = valenbisi["geo_point_2d"].apply(lambda x: eval(x))

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
        start_time = st.time_input("Start Time")

    if start_location and end_location:
        st.success(
            f"Planning route from **{start_location}** to **{end_location}** starting at **{start_time.strftime('%H:%M')}**"
        )

        start_coords = geocode_location(start_location, "start")
        end_coords = geocode_location(end_location, "end")

        if start_coords:
            st.write(
                f"Start location coordinates: {start_coords.latitude}, {start_coords.longitude}"
            )
            start_station = find_closest_point(
                valenbisi,
                (start_coords.latitude, start_coords.longitude),
                coord_col="geo_point_2d",
            )
            st.write(
                f"Closest starting Valenbisi station: {start_station['Direccion']} at {start_station['geo_point_2d']}"
            )
        else:
            st.error("Could not find the start location. Please check the input.")

        if end_coords:
            st.write(
                f"End location coordinates: {end_coords.latitude}, {end_coords.longitude}"
            )
            end_station = find_closest_point(
                valenbisi,
                (end_coords.latitude, end_coords.longitude),
                coord_col="geo_point_2d",
            )
            st.write(
                f"Closest ending Valenbisi station: {end_station['Direccion']} at {end_station['geo_point_2d']}"
            )
        else:
            st.error("Could not find the end location. Please check the input.")

        if start_coords and end_coords:
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
                ],
                popup=start_station["Direccion"],
                icon=folium.Icon(color="green", icon="bicycle", prefix="fa"),
            ).add_to(m)

            folium.Marker(
                location=[
                    end_station["geo_point_2d"][0],
                    end_station["geo_point_2d"][1],
                ],
                popup=end_station["Direccion"],
                icon=folium.Icon(color="orange", icon="bicycle", prefix="fa"),
            ).add_to(m)

            st_folium(m, width=700, height=500)
    else:
        st.info("Please enter both start and end locations to view the route.")


if __name__ == "__main__":
    main()
