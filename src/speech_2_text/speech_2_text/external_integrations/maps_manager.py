"""
Gestor de Google Maps para el agente NAO.

Funcionalidades:
    - Detección de ubicación del dispositivo (GPS → WiFi Geolocation → IP fallback)
    - Búsqueda de lugares (text search, nearby)
    - Tráfico y condiciones de ruta (Directions API con tráfico en tiempo real)
    - Distancia y tiempo entre dos puntos (Distance Matrix API)
    - Detalles de un lugar (Place Details API)
    - Generación de URLs útiles para Telegram:
        · Static Maps (imágenes de mapa)
        · Street View
        · Directions (rutas abribles en Google Maps)
        · Búsqueda directa en Google Maps
        · Link de lugar por Place ID

Requiere:
    GOOGLE_MAPS_API_KEY en .env
    pip install googlemaps requests

Para ubicación por WiFi (Ubuntu):
    nmcli (viene con NetworkManager, disponible en Ubuntu por defecto)
    GOOGLE_MAPS_API_KEY con Geolocation API habilitada

Para ubicación por GPS (Ubuntu):
    sudo apt install gpsd gpsd-clients python3-gps
    sudo systemctl enable gpsd
"""

import os
import subprocess
import json
import time
import re
import requests
from urllib.parse import urlencode, quote_plus
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv, find_dotenv
import googlemaps

# Buscar .env
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(
    filename='.env', raise_error_if_not_found=False, usecwd=False
)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# ─────────────────────────────────────────────
# DECLARACIONES DE FUNCIONES PARA GEMINI
# ─────────────────────────────────────────────
MAPS_FUNCTIONS = [
    {
        "name": "search_places",
        "description": (
            "Busca lugares, negocios, restaurantes, hospitales, tiendas u otros sitios usando Google Maps. "
            "Devuelve nombre, dirección, rating, horario y enlace directo. "
            "Úsalo cuando el usuario pregunte por lugares cercanos o en una ciudad específica."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Qué buscar, por ejemplo 'restaurantes italianos cerca de mí', 'hospital en Medellín'"
                },
                "location": {
                    "type": "string",
                    "description": (
                        "Ubicación de referencia para la búsqueda. "
                        "Si el usuario dice 'cerca de mí' o similar, deja este campo vacío y se usará la ubicación del dispositivo. "
                        "Si el usuario menciona una ciudad o dirección, ponla aquí."
                    )
                },
                "radius_km": {
                    "type": "number",
                    "description": "Radio de búsqueda en kilómetros (default: 5)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de resultados (default: 5, máximo 10)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_directions",
        "description": (
            "Obtiene indicaciones de ruta entre dos puntos, incluyendo distancia, tiempo estimado "
            "y condiciones de tráfico en tiempo real. "
            "El link de Google Maps con la ruta se envía automáticamente a Telegram — NO es necesario llamar send_telegram_link por separado. "
            "Úsalo cuando el usuario pregunte cómo llegar a un lugar, cuánto tarda en llegar, o cómo está el tráfico."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destino de la ruta (nombre de lugar, dirección, o coordenadas)"
                },
                "origin": {
                    "type": "string",
                    "description": (
                        "Punto de partida. Si el usuario dice 'desde aquí', 'desde mi ubicación' o similar, "
                        "deja vacío para usar la ubicación actual del dispositivo."
                    )
                },
                "mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "bicycling", "transit"],
                    "description": "Medio de transporte (default: driving)"
                },
                "send_telegram_link": {
                    "type": "boolean",
                    "description": "Si se debe enviar el link de la ruta por Telegram (default: true)"
                }
            },
            "required": ["destination"]
        }
    },
    {
        "name": "get_place_details",
        "description": (
            "Obtiene información detallada de un lugar específico: dirección completa, teléfono, "
            "horario de atención, rating, reseñas, sitio web y enlace de Google Maps. "
            "La información se envía automáticamente a Telegram — NO es necesario llamar send_telegram_link por separado. "
            "Úsalo cuando el usuario pregunte por los detalles de un local o negocio específico."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "Nombre del lugar o negocio a buscar"
                },
                "location_hint": {
                    "type": "string",
                    "description": "Ciudad o área para acotar la búsqueda (opcional)"
                },
                "send_telegram_link": {
                    "type": "boolean",
                    "description": "Si se debe enviar el link del lugar por Telegram (default: true)"
                }
            },
            "required": ["place_name"]
        }
    },
    {
        "name": "send_static_map",
        "description": (
            "Genera y envía por Telegram una imagen de mapa estático mostrando una ubicación, "
            "ruta o área. Útil para mostrar visualmente dónde queda un lugar o una ruta."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "center": {
                    "type": "string",
                    "description": (
                        "Centro del mapa: nombre de lugar, dirección o coordenadas 'lat,lng'. "
                        "Si es 'mi ubicación' o similar, deja vacío para usar la ubicación del dispositivo."
                    )
                },
                "zoom": {
                    "type": "integer",
                    "description": "Nivel de zoom del mapa (1=mundo, 15=barrio, 20=edificio). Default: 14"
                },
                "markers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de marcadores adicionales a mostrar en el mapa (nombre o 'lat,lng')"
                },
                "map_type": {
                    "type": "string",
                    "enum": ["roadmap", "satellite", "terrain", "hybrid"],
                    "description": "Tipo de mapa (default: roadmap)"
                },
                "caption": {
                    "type": "string",
                    "description": "Texto descriptivo para acompañar la imagen en Telegram"
                }
            },
            "required": []
        }
    },
    {
        "name": "send_street_view",
        "description": (
            "Genera y envía por Telegram una imagen de Street View de una ubicación. "
            "Útil para que el usuario vea cómo luce un lugar desde la calle."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Dirección o nombre del lugar para ver en Street View"
                },
                "heading": {
                    "type": "number",
                    "description": "Ángulo de la cámara en grados (0=Norte, 90=Este, 180=Sur, 270=Oeste). Opcional."
                },
                "caption": {
                    "type": "string",
                    "description": "Texto descriptivo para acompañar la imagen en Telegram"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_traffic_info",
        "description": (
            "Obtiene información del tráfico actual en una ruta o zona. "
            "El resumen de tráfico y el link de ruta se envían automáticamente a Telegram — NO es necesario llamar send_telegram_link por separado. "
            "Responde preguntas como '¿cómo está el tráfico para ir a X?', "
            "'¿cuánto tarda ir al trabajo con el tráfico de ahora?'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destino de la ruta"
                },
                "origin": {
                    "type": "string",
                    "description": "Origen. Si está vacío, usa la ubicación actual del dispositivo."
                }
            },
            "required": ["destination"]
        }
    }
]


# ─────────────────────────────────────────────
# DETECCIÓN DE UBICACIÓN
# ─────────────────────────────────────────────

def _get_location_by_gps(timeout: int = 5) -> Optional[Tuple[float, float]]:
    """
    Intenta obtener coordenadas GPS via gpsd.
    Requiere: sudo apt install gpsd gpsd-clients python3-gps
    """
    try:
        import gps as gpsd_module  # python3-gps / gps3
        session = gpsd_module.gps(mode=gpsd_module.WATCH_ENABLE | gpsd_module.WATCH_NEWSTYLE)
        deadline = time.time() + timeout
        while time.time() < deadline:
            report = session.next()
            if report['class'] == 'TPV':
                lat = getattr(report, 'lat', None)
                lon = getattr(report, 'lon', None)
                if lat and lon and lat != 0 and lon != 0:
                    print(f"[Location] 📡 GPS: {lat}, {lon}")
                    return (lat, lon)
    except Exception as e:
        print(f"[Location] GPS no disponible: {e}")
    return None


def _get_location_by_wifi(api_key: str) -> Optional[Tuple[float, float]]:
    """
    Obtiene coordenadas escaneando redes WiFi cercanas y usando Google Geolocation API.
    Requiere: nmcli (viene con NetworkManager en Ubuntu)
    """
    try:
        # Escanear redes WiFi con nmcli
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'BSSID,SIGNAL,CHAN,FREQ', 'dev', 'wifi', 'list', '--rescan', 'yes'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise RuntimeError(f"nmcli error: {result.stderr}")

        wifi_aps = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 4:
                # BSSID tiene el formato XX\:XX\:XX\:XX\:XX\:XX en nmcli
                bssid_raw = ':'.join(parts[:6]).replace('\\:', ':')
                try:
                    signal = int(parts[6])
                    channel = int(parts[7])
                except (ValueError, IndexError):
                    signal, channel = -70, 6

                wifi_aps.append({
                    "macAddress": bssid_raw,
                    "signalStrength": signal,
                    "channel": channel
                })

        if not wifi_aps:
            return None

        # Llamar a Google Geolocation API
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}"
        payload = {"wifiAccessPoints": wifi_aps[:20]}  # máximo 20 APs
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lat = data['location']['lat']
        lng = data['location']['lng']
        accuracy = data.get('accuracy', 0)
        print(f"[Location] 📶 WiFi Geolocation: {lat}, {lng} (±{accuracy:.0f}m)")
        return (lat, lng)

    except Exception as e:
        print(f"[Location] WiFi geolocation no disponible: {e}")
    return None


def _get_location_by_ip() -> Optional[Tuple[float, float]]:
    """
    Obtiene coordenadas aproximadas por IP pública (fallback, precisión ~ciudad).
    No requiere API key.
    """
    try:
        resp = requests.get('http://ip-api.com/json/?fields=lat,lon,city,country,status', timeout=8)
        data = resp.json()
        if data.get('status') == 'success':
            lat, lon = data['lat'], data['lon']
            print(f"[Location] 🌐 IP geolocation: {lat}, {lon} ({data.get('city')}, {data.get('country')})")
            return (lat, lon)
    except Exception as e:
        print(f"[Location] IP geolocation no disponible: {e}")
    return None


def get_device_location(api_key: str = None) -> Optional[Tuple[float, float]]:
    """
    Obtiene la ubicación del dispositivo usando múltiples métodos en orden de precisión:
    1. GPS (más preciso, requiere hardware GPS o gpsd)
    2. WiFi Geolocation (Google API, buena precisión en interiores)
    3. IP Geolocation (fallback, precisión a nivel de ciudad)

    Returns:
        Tupla (lat, lng) o None si todos los métodos fallan.
    """
    # 1. GPS
    loc = _get_location_by_gps(timeout=4)
    if loc:
        return loc

    # 2. WiFi (necesita API key para Geolocation API)
    key = api_key or GOOGLE_MAPS_API_KEY
    if key:
        loc = _get_location_by_wifi(key)
        if loc:
            return loc

    # 3. IP fallback
    loc = _get_location_by_ip()
    return loc


# ─────────────────────────────────────────────
# GENERADORES DE URLs
# ─────────────────────────────────────────────

def _maps_search_url(query: str) -> str:
    """URL de búsqueda directa en Google Maps."""
    return f"https://www.google.com/maps/search/{quote_plus(query)}"


def _maps_directions_url(origin: str, destination: str, mode: str = "driving") -> str:
    """URL de ruta entre dos puntos (abre en Google Maps)."""
    params = urlencode({
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": mode
    })
    return f"https://www.google.com/maps/dir/?{params}"


def _maps_place_url(place_id: str) -> str:
    """URL de detalle de un lugar por Place ID."""
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}"


def _static_map_url(
    api_key: str,
    center: str,
    zoom: int = 14,
    size: str = "600x400",
    markers: List[str] = None,
    map_type: str = "roadmap",
    path: str = None
) -> str:
    """Genera URL de Static Maps API."""
    params = [
        ("center", center),
        ("zoom", str(zoom)),
        ("size", size),
        ("maptype", map_type),
        ("key", api_key),
        ("markers", f"color:red|{center}"),
    ]
    if markers:
        for m in markers:
            params.append(("markers", f"color:blue|{m}"))
    if path:
        params.append(("path", path))

    query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params)
    return f"https://maps.googleapis.com/maps/api/staticmap?{query}"


def _street_view_image_url(
    api_key: str,
    location: str,
    size: str = "600x400",
    heading: float = None,
    fov: int = 90,
    pitch: int = 0
) -> str:
    """Genera URL de Street View Static API (imagen)."""
    params = {
        "location": location,
        "size": size,
        "fov": fov,
        "pitch": pitch,
        "key": api_key
    }
    if heading is not None:
        params["heading"] = heading
    return f"https://maps.googleapis.com/maps/api/streetview?{urlencode(params)}"


def _street_view_explore_url(location: str) -> str:
    """URL para abrir Street View en Google Maps (navegable)."""
    return f"https://www.google.com/maps/@?api=1&map_action=pano&query={quote_plus(location)}"


# ─────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────

class MapsManager:
    """Gestor de Google Maps para el agente NAO."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise ValueError(
                "Se requiere GOOGLE_MAPS_API_KEY en .env\n"
                "Habilita las APIs en: https://console.cloud.google.com/"
            )
        self.client = googlemaps.Client(key=self.api_key)
        self._device_location: Optional[Tuple[float, float]] = None
        print("[MapsManager] ✅ Google Maps inicializado")

    def refresh_location(self) -> Optional[Tuple[float, float]]:
        """Detecta y almacena la ubicación actual del dispositivo."""
        self._device_location = get_device_location(self.api_key)
        return self._device_location

    def get_current_location(self) -> Optional[Tuple[float, float]]:
        """Retorna la ubicación actual (la detecta si aún no se ha hecho)."""
        if not self._device_location:
            self.refresh_location()
        return self._device_location

    def _resolve_location_str(self, location_input: Optional[str]) -> Optional[str]:
        """
        Convierte una ubicación de entrada a string usable por la API.
        Si es None o vacío, usa la ubicación del dispositivo.
        """
        if location_input and location_input.strip():
            return location_input.strip()
        loc = self.get_current_location()
        if loc:
            return f"{loc[0]},{loc[1]}"
        return None

    # ── SEARCH PLACES ──────────────────────────────────────────────────

    def search_places(
        self,
        query: str,
        location: str = None,
        radius_km: float = 5,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Busca lugares usando Text Search API."""
        try:
            loc_str = self._resolve_location_str(location)
            kwargs = {"query": query}

            if loc_str:
                # Geocodificar si es texto, o parsear si es "lat,lng"
                if re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*$', loc_str):
                    lat, lng = map(float, loc_str.split(','))
                else:
                    geo = self.client.geocode(loc_str)
                    if geo:
                        lat = geo[0]['geometry']['location']['lat']
                        lng = geo[0]['geometry']['location']['lng']
                    else:
                        lat, lng = None, None

                if lat and lng:
                    kwargs["location"] = (lat, lng)
                    kwargs["radius"] = int(radius_km * 1000)

            response = self.client.places(**kwargs)
            results_raw = response.get('results', [])[:max_results]

            results = []
            for place in results_raw:
                place_id = place.get('place_id', '')
                results.append({
                    "name": place.get('name', ''),
                    "address": place.get('formatted_address', place.get('vicinity', '')),
                    "rating": place.get('rating'),
                    "total_ratings": place.get('user_ratings_total'),
                    "open_now": place.get('opening_hours', {}).get('open_now'),
                    "place_id": place_id,
                    "maps_url": _maps_place_url(place_id) if place_id else '',
                    "search_url": _maps_search_url(place.get('name', '') + ' ' + place.get('vicinity', ''))
                })

            return {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "results": results,
                "message": f"Se encontraron {len(results)} resultados para '{query}'"
            }
        except Exception as e:
            return {"status": "error", "message": f"Error buscando lugares: {str(e)}"}

    # ── DIRECTIONS / TRAFFIC ────────────────────────────────────────────

    def get_directions(
        self,
        destination: str,
        origin: str = None,
        mode: str = "driving",
        send_telegram_link: bool = True
    ) -> Dict[str, Any]:
        """Obtiene ruta con información de tráfico en tiempo real."""
        try:
            origin_str = self._resolve_location_str(origin)
            if not origin_str:
                return {"status": "error", "message": "No se pudo determinar el punto de origen"}

            kwargs = {
                "origin": origin_str,
                "destination": destination,
                "mode": mode,
            }
            if mode == "driving":
                kwargs["departure_time"] = "now"
                kwargs["traffic_model"] = "best_guess"

            result = self.client.directions(**kwargs)
            if not result:
                return {"status": "error", "message": f"No se encontró ruta hacia '{destination}'"}

            leg = result[0]['legs'][0]
            distance = leg['distance']['text']
            duration = leg['duration']['text']
            duration_traffic = leg.get('duration_in_traffic', {}).get('text', duration)

            # Pasos de la ruta (resumidos)
            steps = []
            for step in leg['steps'][:5]:
                instruction = re.sub(r'<[^>]+>', '', step.get('html_instructions', ''))
                steps.append(f"{instruction} ({step['distance']['text']})")

            directions_url = _maps_directions_url(origin_str, destination, mode)

            return {
                "status": "success",
                "origin": leg['start_address'],
                "destination": leg['end_address'],
                "distance": distance,
                "duration_no_traffic": duration,
                "duration_with_traffic": duration_traffic,
                "mode": mode,
                "steps_summary": steps,
                "directions_url": directions_url,
                "send_to_telegram": send_telegram_link,
                "message": (
                    f"Ruta a '{destination}': {distance}, "
                    f"~{duration_traffic} con tráfico actual"
                )
            }
        except Exception as e:
            return {"status": "error", "message": f"Error obteniendo ruta: {str(e)}"}

    def get_traffic_info(self, destination: str, origin: str = None) -> Dict[str, Any]:
        """Resumen de condiciones de tráfico hacia un destino."""
        result = self.get_directions(destination, origin, mode="driving")
        if result['status'] != 'success':
            return result

        duration_normal = result['duration_no_traffic']
        duration_traffic = result['duration_with_traffic']
        distance = result['distance']

        # Evaluar congestión comparando tiempos
        def _parse_minutes(text: str) -> int:
            mins = 0
            m = re.search(r'(\d+)\s*hour', text)
            if m:
                mins += int(m.group(1)) * 60
            m = re.search(r'(\d+)\s*min', text)
            if m:
                mins += int(m.group(1))
            return mins

        normal_min = _parse_minutes(duration_normal)
        traffic_min = _parse_minutes(duration_traffic)
        delay = traffic_min - normal_min

        if delay <= 2:
            traffic_status = "fluido"
        elif delay <= 10:
            traffic_status = "moderado"
        elif delay <= 25:
            traffic_status = "con demoras"
        else:
            traffic_status = "muy congestionado"

        return {
            "status": "success",
            "destination": result['destination'],
            "distance": distance,
            "duration_no_traffic": duration_normal,
            "duration_with_traffic": duration_traffic,
            "delay_minutes": delay,
            "traffic_status": traffic_status,
            "directions_url": result['directions_url'],
            "message": (
                f"Tráfico hacia '{destination}': {traffic_status}. "
                f"Distancia: {distance}. "
                f"Tiempo normal: {duration_normal}, con tráfico actual: {duration_traffic}"
                + (f" (demora extra: ~{delay} min)" if delay > 0 else "")
            )
        }

    # ── PLACE DETAILS ───────────────────────────────────────────────────

    def get_place_details(
        self,
        place_name: str,
        location_hint: str = None,
        send_telegram_link: bool = True
    ) -> Dict[str, Any]:
        """Obtiene detalles completos de un lugar."""
        try:
            search_query = place_name
            if location_hint:
                search_query += f" {location_hint}"

            loc_str = self._resolve_location_str(location_hint or None)
            search_kwargs = {"query": search_query}
            if loc_str and re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*$', loc_str):
                lat, lng = map(float, loc_str.split(','))
                search_kwargs["location"] = (lat, lng)
                search_kwargs["radius"] = 20000

            candidates = self.client.find_place(
                input=search_query,
                input_type="textquery",
                fields=["place_id", "name", "formatted_address"]
            )

            if not candidates.get('candidates'):
                return {"status": "error", "message": f"No se encontró '{place_name}'"}

            place_id = candidates['candidates'][0]['place_id']

            details = self.client.place(
                place_id=place_id,
                fields=[
                    "name", "formatted_address", "formatted_phone_number",
                    "opening_hours", "rating", "user_ratings_total",
                    "website", "url", "price_level", "editorial_summary",
                    "reviews"
                ]
            ).get('result', {})

            # Horario
            hours = None
            if 'opening_hours' in details:
                hours = details['opening_hours'].get('weekday_text', [])
                open_now = details['opening_hours'].get('open_now')
            else:
                open_now = None

            # Top reseña
            top_review = None
            if details.get('reviews'):
                r = details['reviews'][0]
                top_review = {
                    "author": r.get('author_name'),
                    "rating": r.get('rating'),
                    "text": r.get('text', '')[:300]
                }

            maps_url = details.get('url') or _maps_place_url(place_id)

            return {
                "status": "success",
                "place_id": place_id,
                "name": details.get('name', place_name),
                "address": details.get('formatted_address', ''),
                "phone": details.get('formatted_phone_number', ''),
                "website": details.get('website', ''),
                "rating": details.get('rating'),
                "total_ratings": details.get('user_ratings_total'),
                "open_now": open_now,
                "schedule": hours,
                "summary": details.get('editorial_summary', {}).get('overview', ''),
                "top_review": top_review,
                "maps_url": maps_url,
                "send_to_telegram": send_telegram_link,
                "message": (
                    f"{details.get('name', place_name)}: "
                    f"{details.get('formatted_address', '')}. "
                    f"Rating: {details.get('rating', 'N/A')}/5. "
                    f"{'Abierto ahora.' if open_now else 'Cerrado ahora.' if open_now is False else ''}"
                )
            }
        except Exception as e:
            return {"status": "error", "message": f"Error obteniendo detalles: {str(e)}"}

    # ── STATIC MAP ──────────────────────────────────────────────────────

    def get_static_map_url(
        self,
        center: str = None,
        zoom: int = 14,
        markers: List[str] = None,
        map_type: str = "roadmap",
        caption: str = None
    ) -> Dict[str, Any]:
        """Genera URL de Static Map para enviar como imagen por Telegram."""
        try:
            center_str = self._resolve_location_str(center)
            if not center_str:
                return {"status": "error", "message": "No se pudo determinar la ubicación para el mapa"}

            url = _static_map_url(
                api_key=self.api_key,
                center=center_str,
                zoom=zoom,
                markers=markers,
                map_type=map_type
            )

            return {
                "status": "success",
                "static_map_url": url,
                "center": center_str,
                "zoom": zoom,
                "caption": caption or f"Mapa de {center or 'tu ubicación actual'}",
                "message": f"Mapa generado para '{center or 'ubicación actual'}'"
            }
        except Exception as e:
            return {"status": "error", "message": f"Error generando mapa: {str(e)}"}

    # ── STREET VIEW ─────────────────────────────────────────────────────

    def get_street_view(
        self,
        location: str,
        heading: float = None,
        caption: str = None
    ) -> Dict[str, Any]:
        """Genera URL de Street View estático para enviar por Telegram."""
        try:
            image_url = _street_view_image_url(
                api_key=self.api_key,
                location=location,
                heading=heading
            )
            explore_url = _street_view_explore_url(location)

            return {
                "status": "success",
                "street_view_image_url": image_url,
                "street_view_explore_url": explore_url,
                "location": location,
                "caption": caption or f"Street View: {location}",
                "message": f"Street View de '{location}' generado"
            }
        except Exception as e:
            return {"status": "error", "message": f"Error generando Street View: {str(e)}"}


# ─────────────────────────────────────────────
# TEST RÁPIDO
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Maps Manager - Prueba")
    print("=" * 60)

    try:
        manager = MapsManager()

        print("\n1. Detectando ubicación del dispositivo...")
        loc = manager.refresh_location()
        print(f"   Ubicación: {loc}")

        print("\n2. Buscando restaurantes cercanos...")
        result = manager.search_places("restaurantes", max_results=3)
        print(f"   {result.get('message')}")
        for r in result.get('results', []):
            print(f"   - {r['name']} | {r['address']} | ⭐{r.get('rating', 'N/A')}")

        print("\n3. Tráfico hacia el aeropuerto El Dorado...")
        result = manager.get_traffic_info("Aeropuerto El Dorado Bogotá")
        print(f"   {result.get('message')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
