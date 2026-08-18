import time
import requests


LEXINGTON_LAT = 38.0406
LEXINGTON_LON = -84.5037

NWS_BASE = "https://api.weather.gov"

NWS_HEADERS = {
    "User-Agent": (
        "LexingtonFirePWA/1.0 "
        "(https://lfd.icebreaker1979.foo)"
    ),
    "Accept": "application/geo+json"
}

CACHE_SECONDS = 300

_weather_cache = {
    "timestamp": 0,
    "data": None
}


def c_to_f(value):
    if value is None:
        return None

    return round((value * 9 / 5) + 32)


def kmh_to_mph(value):
    if value is None:
        return None

    return round(value * 0.621371)


def pa_to_inhg(value):
    if value is None:
        return None

    return round(value * 0.0002953, 2)


def compass_direction(degrees):
    if degrees is None:
        return None

    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]

    index = round(degrees / 22.5) % 16

    return directions[index]


def nws_get(url):
    response = requests.get(
        url,
        headers=NWS_HEADERS,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


def get_latest_observation(stations_url):
    stations_data = nws_get(stations_url)

    features = stations_data.get("features", [])

    if not features:
        return None

    station = features[0]

    station_id = station.get("properties", {}).get(
        "stationIdentifier"
    )

    station_name = station.get("properties", {}).get(
        "name",
        station_id
    )

    if not station_id:
        return None

    observation_url = (
        f"{NWS_BASE}/stations/"
        f"{station_id}/observations/latest"
    )

    observation = nws_get(observation_url)

    props = observation.get("properties", {})

    temperature_c = (
        props.get("temperature", {})
        .get("value")
    )

    dewpoint_c = (
        props.get("dewpoint", {})
        .get("value")
    )

    humidity = (
        props.get("relativeHumidity", {})
        .get("value")
    )

    wind_speed_kmh = (
        props.get("windSpeed", {})
        .get("value")
    )

    wind_gust_kmh = (
        props.get("windGust", {})
        .get("value")
    )

    wind_direction_degrees = (
        props.get("windDirection", {})
        .get("value")
    )

    pressure_pa = (
        props.get("barometricPressure", {})
        .get("value")
    )

    heat_index_c = (
        props.get("heatIndex", {})
        .get("value")
    )

    wind_chill_c = (
        props.get("windChill", {})
        .get("value")
    )

    feels_like = None

    if heat_index_c is not None:
        feels_like = c_to_f(heat_index_c)

    elif wind_chill_c is not None:
        feels_like = c_to_f(wind_chill_c)

    else:
        feels_like = c_to_f(temperature_c)

    return {
        "station": station_id,
        "station_name": station_name,
        "timestamp": props.get("timestamp"),
        "description": (
            props.get("textDescription")
            or "Current conditions"
        ),
        "temperature_f": c_to_f(
            temperature_c
        ),
        "feels_like_f": feels_like,
        "dewpoint_f": c_to_f(
            dewpoint_c
        ),
        "humidity_percent": (
            round(humidity)
            if humidity is not None
            else None
        ),
        "wind_direction": compass_direction(
            wind_direction_degrees
        ),
        "wind_direction_degrees": (
            round(wind_direction_degrees)
            if wind_direction_degrees is not None
            else None
        ),
        "wind_speed_mph": kmh_to_mph(
            wind_speed_kmh
        ),
        "wind_gust_mph": kmh_to_mph(
            wind_gust_kmh
        ),
        "pressure_inhg": pa_to_inhg(
            pressure_pa
        )
    }


def get_forecast(forecast_url):
    forecast_data = nws_get(forecast_url)

    periods = (
        forecast_data
        .get("properties", {})
        .get("periods", [])
    )

    output = []

    for period in periods[:6]:
        probability = (
            period
            .get(
                "probabilityOfPrecipitation",
                {}
            )
            .get("value")
        )

        output.append({
            "number": period.get("number"),
            "name": period.get("name"),
            "start_time": period.get(
                "startTime"
            ),
            "end_time": period.get(
                "endTime"
            ),
            "is_daytime": period.get(
                "isDaytime"
            ),
            "temperature": period.get(
                "temperature"
            ),
            "temperature_unit": period.get(
                "temperatureUnit"
            ),
            "wind_speed": period.get(
                "windSpeed"
            ),
            "wind_direction": period.get(
                "windDirection"
            ),
            "short_forecast": period.get(
                "shortForecast"
            ),
            "detailed_forecast": period.get(
                "detailedForecast"
            ),
            "precipitation_percent": probability
        })

    return output


def get_alerts(county_zone_url):
    zone_id = county_zone_url.rstrip("/").split("/")[-1]

    alerts_url = (
        f"{NWS_BASE}/alerts/active"
        f"?zone={zone_id}"
    )

    alert_data = nws_get(alerts_url)

    alerts = []

    for feature in alert_data.get("features", []):
        props = feature.get("properties", {})

        alerts.append({
            "id": props.get("id"),
            "event": props.get("event"),
            "headline": props.get("headline"),
            "severity": props.get("severity"),
            "certainty": props.get("certainty"),
            "urgency": props.get("urgency"),
            "area": props.get("areaDesc"),
            "effective": props.get("effective"),
            "onset": props.get("onset"),
            "expires": props.get("expires"),
            "ends": props.get("ends"),
            "description": props.get(
                "description"
            ),
            "instruction": props.get(
                "instruction"
            )
        })

    return alerts


def get_fayette_alerts():
    fayette_zone_url = (
        f"{NWS_BASE}/zones/county/KYC067"
    )

    return get_alerts(
        fayette_zone_url
    )

def build_weather_data():
    point_url = (
        f"{NWS_BASE}/points/"
        f"{LEXINGTON_LAT},{LEXINGTON_LON}"
    )

    point_data = nws_get(point_url)

    props = point_data.get("properties", {})

    forecast_url = props.get("forecast")

    stations_url = props.get(
        "observationStations"
    )

    county_zone_url = props.get("county")

    if not forecast_url:
        raise RuntimeError(
            "NWS did not return a forecast URL."
        )

    if not stations_url:
        raise RuntimeError(
            "NWS did not return observation stations."
        )

    if not county_zone_url:
        raise RuntimeError(
            "NWS did not return a county zone."
        )

    current = get_latest_observation(
        stations_url
    )

    forecast = get_forecast(
        forecast_url
    )

    alerts = get_alerts(
        county_zone_url
    )

    return {
        "success": True,
        "location": {
            "name": "Lexington",
            "state": "KY",
            "latitude": LEXINGTON_LAT,
            "longitude": LEXINGTON_LON,
            "county_zone": (
                county_zone_url
                .rstrip("/")
                .split("/")[-1]
            )
        },
        "current": current,
        "forecast": forecast,
        "alerts": alerts,
        "alert_count": len(alerts),
        "links": {
            "radar": "https://radar.weather.gov/",
            "forecast": (
                "https://forecast.weather.gov/"
                "MapClick.php?"
                "lat=38.0406&lon=-84.5037"
            )
        },
        "source": (
            "NOAA / National Weather Service"
        )
    }


def get_weather_data(force=False):
    now = time.time()

    age = (
        now -
        _weather_cache["timestamp"]
    )

    if (
        not force
        and _weather_cache["data"] is not None
        and age < CACHE_SECONDS
    ):
        return _weather_cache["data"]

    data = build_weather_data()

    _weather_cache["data"] = data
    _weather_cache["timestamp"] = now

    return data
