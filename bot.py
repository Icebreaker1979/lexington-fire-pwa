import requests
from bs4 import BeautifulSoup
from pywebpush import webpush, WebPushException
from weather_service import get_fayette_alerts
import time
import json
import os
import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATUS_URL = "https://fire.lexingtonky.gov/open/status/status.htm"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
PUSH_SUBSCRIPTIONS_FILE = "/var/lib/lfd-bot/push_subscriptions.json"
PUSH_PREFERENCES_FILE = "/var/lib/lfd-bot/push_preferences.json"
VAPID_PRIVATE_KEY = "/opt/lfd-bot/private_key.pem"
VAPID_SUBJECT = "mailto:admin@icebreaker1979.foo"
STATE_FILE = "/var/lib/lfd-bot/seen_incidents.json"
WEATHER_ALERT_STATE_FILE = "/var/lib/lfd-bot/seen_weather_alerts.json"

CODES = {
    "FAA1":   "Aircraft Alert 1",
    "FAA2":   "Aircraft Alert 2",
    "FAA3":   "Aircraft Alert 3",
    "FASB":   "Aircraft Standby Bluegrass Station",
    "FASS":   "Assistance",
    "FBAS":   "Barricaded Subject",
    "FBOT":   "Bomb Threat",
    "FBWD":   "Bomb Threat with a Device",
    "FBGL":   "Brush/Grass/Leaf/Tree Fire",
    "FBERTR": "BERT - Rescue",
    "FBERTH": "BERT - HazMat",
    "FCMS":   "Carbon Monoxide Sickness",
    "FCAR":   "Carbon Monoxide Situation",
    "FCHI":   "Chimney Fire",
    "FCOL":   "Collapse Rescue",
    "FCSEPP": "Community Emergency - Bluegrass Army Depot",
    "FCSR":   "Confined Space Rescue",
    "FDVR":   "Dive Rescue Response",
    "FDUM":   "Dumpster Fire",
    "FELC":   "Electrical Cutoff",
    "FELF":   "Electrical Fire",
    "FWID":   "Wires Down",
    "FUTL":   "Utility Cutoff",
    "FELS":   "Elevator Situation",
    "FEXP":   "Explosion",
    "FFIA":   "Fire in an Appliance",
    "FDET":   "Fire Detail",
    "FFHMR":  "Full HazMat Response",
    "FGAC":   "Gas Cutoff",
    "FGAS":   "Gasoline/Fuel Leak",
    "FHMC":   "Hazardous Material",
    "FSCU":   "HazMat - MVC General Spill Clean Up",
    "FHCL":   "HazMat - Clandestine Lab",
    "FMERC":  "HazMat - Mercury Spill",
    "FHGEO":  "HazMat - Natural Gas from Geothermal/Water Well",
    "FINV":   "Investigation",
    "FLAR":   "Large Animal Rescue",
    "FLIFT":  "Lift Assist",
    "FLOI":   "Lock In/Lock Out",
    "FMAI":   "Mailbox Fire",
    "FMDR":   "Mass Decon Response - Kroger Field",
    "FMIS":   "Missing Person",
    "FNGL":   "Natural Gas Leak",
    "FGAO":   "Natural Gas Odor",
    "FOTF":   "Other Fire",
    "FOTS":   "Other Service",
    "FK9R":   "Out of County Investigation K-9 Response",
    "FPRT":   "Private/Telephone Alarm",
    "FPLB":   "Reduced Response (Plan B)",
    "FWAR":   "Remove Water",
    "FROP":   "Rope/High Angle Rescue",
    "FSIA":   "Smoke in the Area - Outdoors",
    "FSMO":   "Smoke in Area/Structure/Odor",
    "FSRCU":  "Special Rescue Related to Civil Unrest",
    "FSTR":   "Structure Fire",
    "FSTRW":  "Structure Fire - Working",
    "FTRA":   "Train Accident",
    "FTRN":   "Transformer Fire",
    "FTRS":   "Trash Fire",
    "FTRE":   "Trench Rescue",
    "FUNT":   "Unknown Trouble",
    "FVIS":   "Vehicle in a Structure",
    "FVAJ":   "Vehicle Accident with JAWS",
    "FVEH":   "Vehicle Fire",
    "FVNS":   "Vehicle Fire Near a Structure",
    "FVLA":   "Vehicle Fire - Large Vehicle",
    "FWAC":   "Water Cutoff",
    "FWTR":   "Water Rescue",
    "MED":    "Medical Response",
    "FVEA":   "Vehicle Accident",
}

ALLOWED_CODES = {
    "FSTR", "FSTRW",
    "FVEH", "FVNS", "FVLA",
    "FBGL", "FDUM", "FTRS", "FOTF",
    "FCHI", "FFIA", "FVIS", "FMAI",
    "FELF", "FTRN", "FWID", "FUTL",
    "FHMC", "FFHMR", "FHCL", "FMERC", "FHGEO", "FBERTH", "FSCU",
    "FCOL", "FCSR", "FDVR", "FROP", "FTRE", "FLAR", "FBERTR", "FVAJ",
    "FEXP", "FBOT", "FBWD",
    "FAA1", "FAA2", "FAA3",
    "FBAS", "FSRCU", "FMDR", "FCSEPP", "FMIS", "FTRA",
}

def get_emoji_and_color(code):
    code = code.upper()
    if code in ("FSTR", "FSTRW"):                                     return "🏠🔥", 0xFF0000
    if code in ("FVEH", "FVNS", "FVLA"):                             return "🚗🔥", 0xFF4500
    if code in ("FBGL", "FDUM", "FTRS", "FOTF", "FCHI", "FFIA",
                "FVIS", "FMAI"):                                      return "🔥",   0xFF6600
    if code in ("FELF", "FTRN", "FWID", "FUTL"): return "⚡", 0xF1C40F
    if code in ("FHMC", "FFHMR", "FHCL", "FMERC", "FHGEO",
                "FBERTH", "FSCU"):                                    return "☣️",   0xFFD700
    if code in ("FCOL", "FCSR", "FDVR", "FROP", "FTRE", "FLAR",
                "FBERTR", "FVAJ"):                                    return "🆘",   0xE74C3C
    if code in ("FEXP", "FBWD"):                                      return "💥",   0xFF0000
    if code == "FBOT":                                                return "🧨",   0xFF4500
    if code in ("FAA1", "FAA2", "FAA3"):                             return "✈️",   0x2ECC71
    if code in ("FBAS", "FSRCU", "FMDR", "FCSEPP", "FMIS", "FTRA"): return "🚨",   0xC0392B
    return "🚒", 0xFF4500

def fetch_incidents():
    r = requests.get(STATUS_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    incidents = []
    for data_div in soup.select("div.data"):
        incident_id_el = data_div.select_one("div.databox.incident")
        if not incident_id_el:
            continue
        def get(cls, div=data_div):
            el = div.select_one(f"div.databox.{cls}")
            return el.get_text(strip=True) if el else ""
        code = get("type").upper()

        # Grab all apparatus units from the appdata div
        appdata = data_div.select_one("div.appdata")
        if appdata:
            units = [el.get_text(strip=True) for el in appdata.select("div.databox")]
            apparatus = ", ".join(u for u in units if u)
        else:
            apparatus = "N/A"

        incidents.append({
            "id":         get("incident"),
            "code":       code,
            "label":      CODES.get(code, code),
            "alarm":      get("alarm"),
            "enroute":    get("enroute"),
            "arrive":     get("arrive"),
            "address":    get("address"),
            "apparatus":  apparatus,
        })
    return incidents

def send_discord(inc, upgraded=False):
    emoji, color = get_emoji_and_color(inc["code"])
    if upgraded:
        prev_label = CODES.get(inc.get("upgraded_from", ""), inc.get("upgraded_from", ""))
        title = f"{emoji}  Incident #{inc['id']} — UPGRADED"
        description = f"**{prev_label}** → **{inc['label']}**"
    else:
        title = f"{emoji}  Incident #{inc['id']}"
        description = f"**{inc['label']}**"

    payload = {
        "embeds": [{
            "title":       title,
            "description": description,
            "color":       color,
            "fields": [
                {"name": "Code",      "value": inc["code"]       or "N/A", "inline": True},
                {"name": "Alarm",     "value": inc["alarm"]      or "N/A", "inline": True},
                {"name": "Enroute",   "value": inc["enroute"]    or "N/A", "inline": True},
                {"name": "Arrive",    "value": inc["arrive"]     or "N/A", "inline": True},
                {"name": "Address",   "value": inc["address"]    or "N/A", "inline": False},
                {"name": "Apparatus", "value": inc["apparatus"]  or "N/A", "inline": False},
            ],
            "footer":    {"text": "Lexington Fire & Emergency Services"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }]
    }
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=10, verify=False)

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

    os.replace(temp_file, PUSH_SUBSCRIPTIONS_FILE)


def load_push_preferences():
    try:
        with open(PUSH_PREFERENCES_FILE, "r") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_incident_category(code):
    if code == "MED":
        return "medical"

    if code in ("FSTR", "FSTRW"):
        return "structure_fires"

    if code in ("FVEH", "FVNS", "FVLA"):
        return "vehicle_fires"

    if code in (
        "FBGL", "FDUM", "FTRS", "FOTF",
        "FCHI", "FFIA", "FVIS", "FMAI"
    ):
        return "other_fires"

    if code in (
        "FELF", "FTRN", "FWID", "FUTL"
    ):
        return "electrical_utility"

    if code in (
        "FHMC", "FFHMR", "FHCL", "FMERC",
        "FHGEO", "FBERTH", "FSCU"
    ):
        return "hazmat"

    if code in (
        "FCOL", "FCSR", "FDVR", "FROP",
        "FTRE", "FLAR", "FBERTR", "FVAJ"
    ):
        return "rescue"

    return "special"

def send_push_notifications(inc, upgraded=False):
    subscriptions = load_push_subscriptions()
    preferences_by_endpoint = load_push_preferences()

    if not subscriptions:
        print("[Push] No subscribers.")
        return

    if upgraded:
        title = f"🚨 Incident Upgraded — {inc['label']}"
    else:
        title = f"🚒 {inc['label']}"

    body = inc["address"]

    if inc.get("apparatus"):
        body += f"\nUnits: {inc['apparatus']}"

    payload = json.dumps({
        "title": title,
        "body": body,
        "incident_id": inc["id"],
        "code": inc["code"],
        "url": "/"
    })

    valid_subscriptions = []

    for subscription in subscriptions:
        endpoint = subscription.get("endpoint", "")

        preferences = preferences_by_endpoint.get(
            endpoint,
            {
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
        )

        category = get_incident_category(
            inc["code"]
        )

        should_send = (
            preferences.get("all_incidents", False)
            or preferences.get(category, False)
        )

        if not should_send:
            valid_subscriptions.append(subscription)

            print(
                f"[Push] Skipped incident #{inc['id']} "
                f"for subscriber preference ({category})"
            )

            continue
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_SUBJECT
                },
                ttl=300
            )

            valid_subscriptions.append(subscription)

            print(
                f"[Push] Sent incident #{inc['id']}"
            )

        except WebPushException as exc:
            status_code = None

            if exc.response is not None:
                status_code = exc.response.status_code

            print(
                f"[Push ERROR] Incident #{inc['id']} "
                f"HTTP {status_code}: {exc}"
            )

            # 404 or 410 normally means the browser's
            # push subscription is no longer valid.
            if status_code not in (404, 410):
                valid_subscriptions.append(subscription)

        except Exception as exc:
            print(
                f"[Push ERROR] Incident #{inc['id']}: {exc}"
            )

            valid_subscriptions.append(subscription)

    # Remove expired subscriptions from our list.
    if len(valid_subscriptions) != len(subscriptions):
        save_push_subscriptions(valid_subscriptions)

def send_weather_push_notifications(alert):
    subscriptions = load_push_subscriptions()
    preferences_by_endpoint = load_push_preferences()

    if not subscriptions:
        print("[Weather Push] No subscribers.")
        return

    alert_event = (
        alert.get("event")
        or "NWS Weather Alert"
    )

    alert_headline = (
        alert.get("headline")
        or alert_event
    )

    alert_id = (
        alert.get("id")
        or alert_event
    )

    payload = json.dumps({
        "title": f"⚠️ {alert_event}",
        "body": alert_headline,
        "weather_alert": True,
        "alert_id": alert_id,
        "url": "/"
    })

    valid_subscriptions = []

    for subscription in subscriptions:
        endpoint = subscription.get(
            "endpoint",
            ""
        )

        preferences = (
            preferences_by_endpoint.get(
                endpoint,
                {}
            )
        )

        weather_enabled = (
            preferences.get(
                "weather_alerts",
                False
            )
        )

        if not weather_enabled:
            valid_subscriptions.append(
                subscription
            )

            print(
                f"[Weather Push] Skipped "
                f"{alert_event} for subscriber preference"
            )

            continue

        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_SUBJECT
                },
                ttl=300
            )

            valid_subscriptions.append(
                subscription
            )

            print(
                f"[Weather Push] Sent: "
                f"{alert_event}"
            )

        except WebPushException as exc:
            status_code = None

            if exc.response is not None:
                status_code = (
                    exc.response.status_code
                )

            print(
                f"[Weather Push ERROR] "
                f"HTTP {status_code}: {exc}"
            )

            if status_code not in (404, 410):
                valid_subscriptions.append(
                    subscription
                )

        except Exception as exc:
            print(
                f"[Weather Push ERROR] {exc}"
            )

            valid_subscriptions.append(
                subscription
            )

    if (
        len(valid_subscriptions)
        != len(subscriptions)
    ):
        save_push_subscriptions(
            valid_subscriptions
        )

def check_weather_alerts(seen_weather_alerts):
    try:
        alerts = get_fayette_alerts()

        active_alert_ids = set()

        for alert in alerts:
            alert_id = alert.get("id")

            if not alert_id:
                continue

            active_alert_ids.add(alert_id)

            if alert_id in seen_weather_alerts:
                continue

            print(
                f"[Weather] New alert: "
                f"{alert.get('event', 'Weather Alert')}"
            )

            send_weather_push_notifications(
                alert
            )

            seen_weather_alerts.add(
                alert_id
            )

        save_seen_weather_alerts(
            seen_weather_alerts
        )

        return seen_weather_alerts

    except Exception as exc:
        print(
            f"[Weather ERROR] {exc}"
        )

        return seen_weather_alerts

def load_seen_weather_alerts():
    try:
        with open(WEATHER_ALERT_STATE_FILE, "r") as f:
            data = json.load(f)

        if isinstance(data, list):
            return set(data)

        return set()

    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen_weather_alerts(alert_ids):
    os.makedirs(
        os.path.dirname(WEATHER_ALERT_STATE_FILE),
        exist_ok=True
    )

    temp_file = WEATHER_ALERT_STATE_FILE + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(
            sorted(alert_ids),
            f,
            indent=2
        )

    os.replace(
        temp_file,
        WEATHER_ALERT_STATE_FILE
    )

def load_seen():
    try:
        data = json.load(open(STATE_FILE))
        # Handle old format (list of IDs) gracefully
        if isinstance(data, list):
            return {inc_id: "" for inc_id in data}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_seen(seen):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(seen, open(STATE_FILE, "w"))

def main():
    print("LFD Bot started. Watching for incidents...")

    seen = load_seen()
    seen_weather_alerts = load_seen_weather_alerts()

    while True:

        # ---------------------------------
        # Lexington Fire incident checking
        # ---------------------------------
        try:
            incidents = fetch_incidents()

            for inc in incidents:
                inc_id = inc["id"]
                inc_code = inc["code"]
                prev_code = seen.get(inc_id)

                if prev_code is None:
                    # Brand new incident
                    seen[inc_id] = inc_code

                    # Discord only sends selected incident codes
                    if inc_code in ALLOWED_CODES:
                        send_discord(inc)

                    # PWA push checks each subscriber's preferences
                    send_push_notifications(inc)

                    if inc_code in ALLOWED_CODES:
                        print(
                            f"[+] Notified: #{inc_id} "
                            f"{inc_code} — {inc['address']}"
                        )
                    else:
                        print(
                            f"[~] Discord skipped: #{inc_id} "
                            f"{inc_code} — {inc['label']}"
                        )

                elif prev_code != inc_code:
                    # Existing incident changed type
                    seen[inc_id] = inc_code
                    inc["upgraded_from"] = prev_code

                    # Discord still follows ALLOWED_CODES
                    if inc_code in ALLOWED_CODES:
                        send_discord(
                            inc,
                            upgraded=True
                        )

                    # PWA evaluates every changed incident
                    send_push_notifications(
                        inc,
                        upgraded=True
                    )

                    if inc_code in ALLOWED_CODES:
                        print(
                            f"[↑] Upgraded: #{inc_id} "
                            f"{prev_code} → {inc_code} "
                            f"— {inc['address']}"
                        )
                    else:
                        print(
                            f"[~] Discord skipped upgrade: "
                            f"#{inc_id} {prev_code} → {inc_code}"
                        )

            save_seen(seen)

        except Exception as e:
            print(
                f"[Incident ERROR] {e}"
            )


        # ---------------------------------
        # Fayette County NWS alert checking
        # Runs even if fire feed is down.
        # ---------------------------------
        try:
            seen_weather_alerts = check_weather_alerts(
                seen_weather_alerts
            )

        except Exception as e:
            print(
                f"[Weather Loop ERROR] {e}"
            )


        time.sleep(45)

if __name__ == "__main__":
    main()
