from flask import Flask, jsonify, send_from_directory, request
from bot import (
    CODES,
    INCIDENT_CODE_GROUPS,
    fetch_incidents,
    get_incident_category
)
from weather_service import get_weather_data
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

PUSH_SUBSCRIPTIONS_FILE = "/var/lib/lfd-bot/push_subscriptions.json"
PUSH_PREFERENCES_FILE = "/var/lib/lfd-bot/push_preferences.json"

VAPID_PUBLIC_KEY = (
    "BJJCgPCrmGRsmUpNDPyVAXqbYGbZEIGVwq2x6lJStFXYvXmDIT4KqfzdlOzfsZx9B-ZXxJHvKBiTx6qcDXzdqHg"
)

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


def load_push_subscriptions():
    try:
        with open(PUSH_SUBSCRIPTIONS_FILE, "r") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_push_subscriptions(subscriptions):
    os.makedirs(
        os.path.dirname(PUSH_SUBSCRIPTIONS_FILE),
        exist_ok=True
    )

    temp_file = PUSH_SUBSCRIPTIONS_FILE + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(subscriptions, f, indent=2)

    os.replace(
        temp_file,
        PUSH_SUBSCRIPTIONS_FILE
    )

def load_push_preferences():
    try:
        with open(PUSH_PREFERENCES_FILE, "r") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_push_preferences(preferences):
    os.makedirs(
        os.path.dirname(PUSH_PREFERENCES_FILE),
        exist_ok=True
    )

    temp_file = PUSH_PREFERENCES_FILE + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(preferences, f, indent=2)

    os.replace(
        temp_file,
        PUSH_PREFERENCES_FILE
    )

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


@app.route("/api/push/public-key")
def push_public_key():
    return jsonify({
        "publicKey": VAPID_PUBLIC_KEY
    })


@app.route("/api/push/subscribe", methods=["POST"])
def push_subscribe():
    subscription = request.get_json(silent=True)

    if not subscription:
        return jsonify({
            "success": False,
            "error": "Missing subscription"
        }), 400

    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys", {})

    if (
        not endpoint
        or not keys.get("p256dh")
        or not keys.get("auth")
    ):
        return jsonify({
            "success": False,
            "error": "Invalid subscription"
        }), 400

    subscriptions = load_push_subscriptions()

    subscriptions = [
        item
        for item in subscriptions
        if item.get("endpoint") != endpoint
    ]

    subscriptions.append(subscription)

    save_push_subscriptions(subscriptions)

    return jsonify({
        "success": True,
        "subscriptions": len(subscriptions)
    })


@app.route("/api/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    payload = request.get_json(silent=True) or {}

    endpoint = payload.get("endpoint")

    if not endpoint:
        return jsonify({
            "success": False,
            "error": "Missing endpoint"
        }), 400

    subscriptions = load_push_subscriptions()

    subscriptions = [
        item
        for item in subscriptions
        if item.get("endpoint") != endpoint
    ]

    save_push_subscriptions(subscriptions)

    all_preferences = load_push_preferences()

    if endpoint in all_preferences:
        del all_preferences[endpoint]
        save_push_preferences(all_preferences)

    return jsonify({
        "success": True,
        "subscriptions": len(subscriptions)
    })

@app.route("/api/push/preferences", methods=["POST"])
def push_preferences():
    payload = request.get_json(silent=True) or {}

    endpoint = payload.get("endpoint")
    preferences = payload.get("preferences")

    if not endpoint:
        return jsonify({
            "success": False,
            "error": "Missing endpoint"
        }), 400

    if not isinstance(preferences, dict):
        return jsonify({
            "success": False,
            "error": "Missing preferences"
        }), 400

    allowed_keys = {
        "all_incidents",
        "structure_fires",
        "other_fires",
        "vehicle_fires",
        "electrical_utility",
        "hazmat",
        "rescue",
        "special",
        "medical",
        "weather_alerts"
    }

    cleaned = {}

    for key in allowed_keys:
        cleaned[key] = bool(
            preferences.get(
                key,
                False
            )
        )

    incident_codes = preferences.get(
        "incident_codes"
    )

    if incident_codes is not None:
        if not isinstance(
            incident_codes,
            list
        ):
            return jsonify({
                "success": False,
                "error": (
                    "incident_codes "
                    "must be a list"
                )
            }), 400

        cleaned[
            "incident_codes"
        ] = sorted({
            str(code)
            .strip()
            .upper()
            for code in incident_codes
            if str(code).strip()
        })

    all_preferences = load_push_preferences()

    all_preferences[endpoint] = cleaned

    save_push_preferences(all_preferences)

    return jsonify({
        "success": True,
        "preferences": cleaned
    })


@app.route("/api/push/preferences", methods=["GET"])
def get_push_preferences():
    endpoint = request.args.get("endpoint", "")

    if not endpoint:
        return jsonify({
            "success": False,
            "error": "Missing endpoint"
        }), 400

    all_preferences = load_push_preferences()

    saved = all_preferences.get(endpoint)

    if saved is None:
        saved = {
            "all_incidents": False,
            "structure_fires": True,
            "other_fires": True,
            "vehicle_fires": True,
            "electrical_utility": True,
            "hazmat": True,
            "rescue": True,
            "special": True,
            "medical": False,
	    "weather_alerts": False
        }

    return jsonify({
        "success": True,
        "preferences": saved
    })

@app.route("/api/weather")
def weather():
    try:
        return jsonify(
            get_weather_data()
        )

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500

@app.route("/api/incident-codes")
def incident_codes():
    output = []

    for group_name, group in (
        INCIDENT_CODE_GROUPS.items()
    ):
        codes = []

        for code in sorted(
            group["codes"]
        ):
            label = CODES.get(
                code,
                code
            )

            codes.append({
                "code": code,
                "label": label,
                "legacy_category":
                    get_incident_category(code)
            })

        output.append({
            "category": group_name,
            "label": group["label"],
            "codes": codes
        })

    return jsonify({
        "success": True,
        "groups": output
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
