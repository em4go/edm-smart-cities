import streamlit as st
import folium
from geopy.geocoders import Nominatim
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
    nodos_vb_filtrados = set(coord_nodo_map.keys()) - {origen_nodo}

    # Paso 3: Calcular rutas desde origen_nodo a todos los nodos posibles
    longitudes = nx.single_source_dijkstra_path_length(G, origen_nodo, weight="length")

    resultados = []

    # Paso 4: Añadir coordenadas y longitudes válidas
    for nodo in nodos_vb_filtrados:
        if nodo in longitudes:
            coord = coord_nodo_map[nodo]
            distancia = longitudes[nodo]
            resultados.append((coord, distancia))

    # Paso 5: Añadir el nodo origen si está en coord_nodo_map
    if origen_nodo in coord_nodo_map:
        resultados.append((coord_nodo_map[origen_nodo], 0))

    resultados.sort(key=lambda x: x[1])

    return resultados


def ruta_a_destino(G, coord_vb, destino, xs, ys):
    destino_nodo = ox.nearest_nodes(G, destino[1], destino[0])

    # Paso 1: Obtener nodos de coord_vb vectorizado
    nodos_vb = ox.nearest_nodes(G, xs, ys)
    coord_nodo_map = dict(zip(nodos_vb, coord_vb))

    # Paso 2: Quitar nodo destino (se añade al final si hace falta)
    nodos_vb_filtrados = set(coord_nodo_map.keys()) - {destino_nodo}

    # Paso 3: Calcular rutas desde destino_nodo a todos los nodos posibles
    longitudes = nx.single_source_dijkstra_path_length(G, destino_nodo, weight="length")

    resultados = []

    # Paso 4: Añadir coordenadas y longitudes válidas
    for nodo in nodos_vb_filtrados:
        if nodo in longitudes:
            coord = coord_nodo_map[nodo]
            distancia = longitudes[nodo]
            resultados.append((coord, distancia))

    # Paso 5: Añadir el nodo destino si está en coord_nodo_map
    if destino_nodo in coord_nodo_map:
        resultados.append((coord_nodo_map[destino_nodo], 0))

    # Paso 6: Ordenar por distancia ascendente
    resultados.sort(key=lambda x: x[1])

    return resultados


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
