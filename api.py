from flask import Flask, jsonify, send_from_directory
from bot import fetch_incidents
import datetime
import requests
import json
import os
import re

app = Flask(__name__)

GEOCODE_URL = (
    "https://geocode.arcgis.com/arcgis/rest/services/"
    "World/GeocodeServer/findAddressCandidates"
)

GEOCODE_CACHE_FILE = "/var/lib/lfd-bot/geocode_cache.json"


def load_geocode_cache():
    try:
        with open(GEOCODE_CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_geocode_cache(cache):
    os.makedirs(os.path.dirname(GEOCODE_CACHE_FILE), exist_ok=True)

    with open(GEOCODE_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


geocode_cache = load_geocode_cache()


def normalize_address(address):
    """
    Convert Lexington CAD-style addresses such as:

        PALUMBO DR 2700 Blk

    into:

        2700 PALUMBO DR
    """

    address = address.strip()

    match = re.match(
        r"^(.*?)\s+(\d+)\s+Blk$",
        address,
        re.IGNORECASE
    )

    if match:
        street = match.group(1).strip()
        number = match.group(2)

        return f"{number} {street}"

    return address


def geocode_address(address):
    if not address:
        return None

    normalized = normalize_address(address)

    cache_key = normalized.upper()

    if cache_key in geocode_cache:
        return geocode_cache[cache_key]

    search_address = f"{normalized}, Lexington, KY"

    try:
        response = requests.get(
            GEOCODE_URL,
            params={
                "SingleLine": search_address,
                "f": "json",
                "outFields": "Match_addr,Addr_type"
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            result = {
                "latitude": None,
                "longitude": None,
                "geocode_score": 0,
                "matched_address": None
            }

        else:
            best = candidates[0]

            # Require a reasonably strong match.
            if best.get("score", 0) < 80:
                result = {
                    "latitude": None,
                    "longitude": None,
                    "geocode_score": best.get("score", 0),
                    "matched_address": best.get("address")
                }
            else:
                location = best.get("location", {})

                result = {
                    "latitude": location.get("y"),
                    "longitude": location.get("x"),
                    "geocode_score": best.get("score"),
                    "matched_address": best.get("address")
                }

        geocode_cache[cache_key] = result
        save_geocode_cache(geocode_cache)

        return result

    except Exception as e:
        print(f"[GEOCODE ERROR] {address}: {e}")

        return {
            "latitude": None,
            "longitude": None,
            "geocode_score": 0,
            "matched_address": None
        }


@app.after_request
def add_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def home():
    return send_from_directory(
        "/opt/lfd-bot/web",
        "index.html"
    )

@app.route("/manifest.json")
def manifest():
    return send_from_directory(
        "/opt/lfd-bot/web",
        "manifest.json",
        mimetype="application/manifest+json"
    )


@app.route("/service-worker.js")
def service_worker():
    response = send_from_directory(
        "/opt/lfd-bot/web",
        "service-worker.js",
        mimetype="application/javascript"
    )

    response.headers["Service-Worker-Allowed"] = "/"

    return response


@app.route("/icons/<path:filename>")
def icons(filename):
    return send_from_directory(
        "/opt/lfd-bot/web/icons",
        filename
    )


@app.route("/app")
def web_app():
    return send_from_directory(
        "/opt/lfd-bot/web",
        "index.html"
    )


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
    })


@app.route("/api/incidents")
def incidents():
    try:
        data = fetch_incidents()

        for incident in data:
            geo = geocode_address(
                incident.get("address", "")
            )

            incident.update(geo)

        return jsonify({
            "success": True,
            "count": len(data),
            "updated": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "incidents": data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8765,
        debug=False
    )
