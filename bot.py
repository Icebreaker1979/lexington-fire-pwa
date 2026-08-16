import requests
from bs4 import BeautifulSoup
import time
import json
import os
import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATUS_URL = "https://fire.lexingtonky.gov/open/status/status.htm"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STATE_FILE = "/var/lib/lfd-bot/seen_incidents.json"

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
    "FELF", "FTRN",
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
    if code in ("FELF", "FTRN"):                                      return "⚡🔥", 0xF1C40F
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
    seen = load_seen()  # now a dict of {id: code}
    while True:
        try:
            incidents = fetch_incidents()
            for inc in incidents:
                inc_id = inc["id"]
                inc_code = inc["code"]
                prev_code = seen.get(inc_id)

                if prev_code is None:
                    # Brand new incident
                    seen[inc_id] = inc_code
                    if inc_code in ALLOWED_CODES:
                        send_discord(inc)
                        print(f"[+] Notified: #{inc_id} {inc_code} — {inc['address']}")
                    else:
                        print(f"[~] Skipped:  #{inc_id} {inc_code} — {inc['label']}")

                elif prev_code != inc_code:
                    # Code changed on existing incident
                    seen[inc_id] = inc_code
                    if inc_code in ALLOWED_CODES:
                        inc["upgraded_from"] = prev_code
                        send_discord(inc, upgraded=True)
                        print(f"[↑] Upgraded: #{inc_id} {prev_code} → {inc_code} — {inc['address']}")
                    else:
                        print(f"[~] Changed (not notified): #{inc_id} {prev_code} → {inc_code}")

            save_seen(seen)
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(45)

if __name__ == "__main__":
    main()
