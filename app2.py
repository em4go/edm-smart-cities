import streamlit as st
import datetime
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import osmnx as ox
import networkx as nx


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


def ruta_a_origen(G, coord_vb, origen, xs, ys):
    origen_nodo = ox.nearest_nodes(G, origen[1], origen[0])
    # Paso 1: Obtener nodos de coord_vb en bloque
    nodos_vb = ox.nearest_nodes(G, xs, ys)
    coord_nodo_map = dict(zip(nodos_vb, coord_vb))

    # Paso 2: Evita nodo origen si está en las coords (lo tratamos aparte si hace falta)
    nodos_vb_filtrados = set(nodos_vb) - {origen_nodo}

    # Paso 3: Calcular rutas desde origen_nodo a todos los nodos posibles
    longitudes = nx.single_source_dijkstra_path_length(G, origen_nodo, weight="length")

    mejor_coord = None
    longitud_minima = float("inf")

    for nodo in nodos_vb_filtrados:
        if nodo in longitudes and longitudes[nodo] < longitud_minima:
            longitud_minima = longitudes[nodo]
            mejor_coord = coord_nodo_map[nodo]

    # Paso 5 (opcional): tratar el caso donde origen ya es uno de los nodos objetivo
    if origen_nodo in coord_nodo_map:
        mejor_coord = coord_nodo_map[origen_nodo]
        longitud_minima = 0

    return mejor_coord


def ruta_a_destino(G, coord_vb, destino, xs, ys):
    destino_nodo = ox.nearest_nodes(G, destino[1], destino[0])
    # Paso 1: Obtener nodos de coord_vb vectorizado
    nodos_vb = ox.nearest_nodes(G, xs, ys)
    coord_nodo_map = dict(zip(nodos_vb, coord_vb))

    # Paso 2: Quitar nodo destino (a menos que queramos comprobarlo aparte)
    nodos_vb_filtrados = set(nodos_vb) - {destino_nodo}

    # Paso 3: Calcular rutas desde destino_nodo a todos los demás nodos
    longitudes = nx.single_source_dijkstra_path_length(G, destino_nodo, weight="length")

    mejor_coord = None
    longitud_minima = float("inf")

    for nodo in nodos_vb_filtrados:
        if nodo in longitudes and longitudes[nodo] < longitud_minima:
            longitud_minima = longitudes[nodo]
            mejor_coord = coord_nodo_map[nodo]

    # Caso especial: el destino está entre las coordenadas
    if destino_nodo in coord_nodo_map:
        mejor_coord = coord_nodo_map[destino_nodo]
        longitud_minima = 0

    return mejor_coord


def crear_ruta(G, coord_vb, origen, destino, xs, ys):
    origen_nodo = ox.nearest_nodes(G, origen[1], origen[0])
    destino_nodo = ox.nearest_nodes(G, destino[1], destino[0])

    est_origen = ruta_a_origen(G, coord_vb, origen, xs, ys)
    est_destino = ruta_a_destino(G, coord_vb, destino, xs, ys)

    est_origen_nodo = ox.nearest_nodes(G, est_origen[1], est_origen[0])
    est_destino_nodo = ox.nearest_nodes(G, est_destino[1], est_destino[0])

    pre_ruta = nx.shortest_path(G, origen_nodo, est_origen_nodo, weight="length")
    ruta = nx.shortest_path(G, est_origen_nodo, est_destino_nodo, weight="length")
    post_ruta = nx.shortest_path(G, est_destino_nodo, destino_nodo, weight="length")

    return pre_ruta, ruta, post_ruta


def add_route_line(G, route, color, m):
    # Obtener coordenadas de cada nodo de la ruta
    latlons = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
    folium.PolyLine(latlons, color=color, weight=5, opacity=0.8).add_to(m)


def main():
    valenbisi = pd.read_csv("data/valenbici_puntos.csv")
    valenbisi["geo_point_2d"] = valenbisi["geo_point_2d"].apply(lambda x: eval(x))

    coord_vb = {x for x in valenbisi["geo_point_2d"]}
    G = ox.graph_from_point(
        (39.4699, -0.3763), dist=3000, network_type="bike", simplify=True
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
            start_station = ruta_a_origen(
                G, coord_vb, (start_coords.latitude, start_coords.longitude), xs, ys
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
            end_station = ruta_a_destino(
                G, coord_vb, (end_coords.latitude, end_coords.longitude), xs, ys
            )
            st.write(
                f"Closest ending Valenbisi station: {end_station['Direccion']} at {end_station['geo_point_2d']}"
            )
        else:
            st.error("Could not find the end location. Please check the input.")

        if start_coords and end_coords:
            pre_ruta, ruta, post_ruta = crear_ruta(
                G,
                coord_vb,
                (start_coords.latitude, start_coords.longitude),
                (end_coords.latitude, end_coords.longitude),
                xs,
                ys,
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

            add_route_line(G, pre_ruta, "blue", m)
            add_route_line(G, ruta, "green", m)
            add_route_line(G, post_ruta, "red", m)

            st_folium(m, width=700, height=500)
    else:
        st.info("Please enter both start and end locations to view the route.")


if __name__ == "__main__":
    main()
