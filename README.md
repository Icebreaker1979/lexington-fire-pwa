# 🚒 Lexington Fire PWA

A self-hosted, installable web application for viewing active **Lexington Fire & Emergency Services** incidents in Lexington, Kentucky.

Built as an Android-friendly alternative inspired by the functionality of the DriveLex iOS app, Lexington Fire PWA provides a mobile incident list, interactive map, incident filtering, location awareness, and optional Discord notifications.

The application runs as a **Progressive Web App (PWA)** and can be installed directly from a supported browser without an app store.

---

## 📱 Features

### Live Incident Feed

Displays current incidents from the publicly available Lexington Fire & Emergency Services incident status feed.

Incident information includes:

- Incident number
- Incident type
- Dispatch code
- Alarm level
- Enroute time
- Arrival time
- Address
- Assigned apparatus

The application automatically refreshes the incident feed so the display stays current.

### 🚨 Incident Filtering

Medical responses can be hidden to make fire, rescue, hazardous materials, and other significant incidents easier to find.

The application recognizes Lexington Fire dispatch codes and translates them into readable incident descriptions.

Examples include:

| Code | Incident |
| --- | --- |
| `FSTR` | Structure Fire |
| `FSTRW` | Structure Fire - Working |
| `FVEH` | Vehicle Fire |
| `FELF` | Electrical Fire |
| `FBGL` | Brush/Grass/Leaf/Tree Fire |
| `FHMC` | Hazardous Material |
| `FVAJ` | Vehicle Accident with JAWS |
| `FEXP` | Explosion |
| `FAA1` | Aircraft Alert 1 |
| `FAA2` | Aircraft Alert 2 |
| `FAA3` | Aircraft Alert 3 |

Different incident categories use different map icons and colors for quick identification.

### 🗺️ Interactive Incident Map

Active incidents are displayed on an interactive Leaflet/OpenStreetMap map.

Features include:

- Incident markers
- Incident-specific icons
- Marker popups
- Address geocoding
- Multiple active incidents displayed simultaneously
- Lexington-area map view
- User location support

Incident addresses are geocoded into latitude and longitude coordinates for map placement.

### 📍 My Location

When accessed over HTTPS, the application can use the browser's geolocation API to display the user's current location on the incident map.

Location access requires user permission and a secure HTTPS connection.

### 📲 Progressive Web App

Lexington Fire PWA can be installed on supported Android devices and desktop browsers.

Once installed, it:

- Launches in standalone mode
- Does not display the browser address bar
- Has its own application icon
- Appears on the home screen/app launcher
- Uses a cached application shell
- Continues retrieving live incident data from the server

The live `/api/` endpoints are intentionally excluded from service-worker caching so incident information is always requested from the server.

### 🔔 Discord Notifications

The included `bot.py` can monitor the incident feed and send selected incidents to a Discord channel using a webhook.

Notifications can be limited to significant incidents such as:

- Structure fires
- Working structure fires
- Vehicle fires
- Hazardous materials incidents
- Rescue incidents
- Explosions
- Bomb threats
- Aircraft alerts
- Other selected emergency events

The bot also detects when an existing incident changes to another dispatch code and can send an **UPGRADED** notification.

---

## 🏗️ Architecture

The project consists of two Python services and a static PWA frontend.

```text
                    Internet / Mobile Device
                             │
                             ▼
                         Cloudflare
                             │
                             ▼
                     Cloudflare Tunnel
                             │
                             ▼
                   Nginx Proxy Manager
                             │
                             ▼
                    Flask API / Web App
                      192.168.x.x:8765
                       │             │
                       │             └──── Web PWA
                       │
                       └──── Lexington Fire Status Feed

                              +

                    Discord Notification Bot
                              │
                              ▼
                         Discord Webhook
```

The application does not require Cloudflare or Nginx Proxy Manager specifically. Any reverse proxy capable of securely exposing the Flask service over HTTPS can be used.

---

## 📁 Project Structure

```text
lexington-fire-pwa/
│
├── api.py
├── bot.py
├── requirements.txt
├── .gitignore
│
└── web/
    ├── index.html
    ├── manifest.json
    ├── service-worker.js
    │
    └── icons/
        ├── icon-192.png
        └── icon-512.png
```

### `api.py`

Provides the Flask backend, incident API, geocoding functionality, and web application routes.

### `bot.py`

Monitors Lexington Fire incidents and optionally sends selected incidents to Discord.

### `web/index.html`

Main mobile web interface containing the incident list and interactive map.

### `web/manifest.json`

Defines PWA metadata including application name, colors, icons, display mode, and startup behavior.

### `web/service-worker.js`

Provides application-shell caching while ensuring live incident API requests remain network-based.

---

## ⚙️ Requirements

The application requires Python 3 and the packages listed in `requirements.txt`.

```text
Flask
requests
beautifulsoup4
Pillow
```

Install the dependencies using:

```bash
python3 -m venv api-venv
source api-venv/bin/activate

pip install -r requirements.txt
```

---

## 🚀 Running the Web Application

Start the API manually with:

```bash
python api.py
```

The application will normally be available at:

```text
http://SERVER-IP:8765/
```

Health status:

```text
http://SERVER-IP:8765/health
```

Incident API:

```text
http://SERVER-IP:8765/api/incidents
```

For production/self-hosted use, running the application as a system service is recommended.

---

## 🔧 Example systemd Service

An example service for the Flask application:

```ini
[Unit]
Description=Lexington Fire Incident API
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/opt/lfd-bot
ExecStart=/opt/lfd-bot/api-venv/bin/python /opt/lfd-bot/api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

After creating the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lfd-api
```

Check its status with:

```bash
sudo systemctl status lfd-api
```

---

## 🔔 Discord Bot Setup

**Never place a Discord webhook directly in `bot.py`.**

The bot expects the webhook to be supplied through the environment variable:

```text
DISCORD_WEBHOOK
```

For example:

```bash
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

For a systemd deployment, store the secret outside the repository.

Example:

```text
/etc/lfd-bot/environment
```

Contents:

```text
DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
```

Protect the file:

```bash
sudo chmod 600 /etc/lfd-bot/environment
```

Then reference it from the service:

```ini
EnvironmentFile=/etc/lfd-bot/environment
```

**Do not commit the environment file or webhook to Git.**

---

## 🌐 HTTPS and Remote Access

Some browser functionality, particularly geolocation and PWA functionality, requires HTTPS.

One possible deployment architecture is:

```text
Cloudflare
     ↓
Cloudflare Tunnel
     ↓
Nginx Proxy Manager
     ↓
Lexington Fire PWA
```

This allows the application to be securely accessed without directly exposing the Flask port to the Internet.

Other reverse proxies and HTTPS configurations can also be used.

---

## 📲 Installing on Android

Open the HTTPS version of the application in Chrome.

Then select:

```text
⋮ → Install app
```

or:

```text
⋮ → Add to Home screen
```

Once installed, Lexington Fire launches in standalone mode without the browser address bar.

---

## 🔐 Security

Keep all credentials outside the Git repository.

The included `.gitignore` is intended to exclude common local/runtime files including:

```text
.env
*.env
api-venv/
venv/
__pycache__/
seen_incidents.json
geocode_cache.json
*.log
*.backup
```

Before publishing changes, it is good practice to verify that no credentials have accidentally been added:

```bash
git status
```

Never commit:

- Discord webhook URLs
- Cloudflare API tokens
- GitHub Personal Access Tokens
- Passwords
- Private keys
- Environment files containing credentials

If a credential is accidentally committed to Git, removing it in a later commit is **not sufficient**. Revoke or rotate the credential immediately.

---

## ⚠️ Disclaimer

This project is an independent community project and is **not affiliated with, endorsed by, or operated by Lexington-Fayette Urban County Government, Lexington Fire & Emergency Services, or any emergency response agency**.

Incident information may be delayed, incomplete, changed, or removed at any time.

**Do not use this application for emergency response, dispatch decisions, navigation to emergency scenes, or personal safety decisions.**

For emergencies, call **911**.

Users should never interfere with emergency personnel or travel to an incident scene solely because it appears in this application.

---

## 🛠️ Built With

- Python
- Flask
- Beautiful Soup
- Requests
- JavaScript
- Leaflet
- OpenStreetMap
- ArcGIS Geocoding
- Progressive Web App technologies
- systemd
- Nginx Proxy Manager
- Cloudflare Tunnel
- Discord Webhooks

---

## 🗺️ Project Background

This project began as a Discord bot that monitored the publicly available Lexington Fire incident feed and posted selected incidents to Discord.

It was later expanded into a mobile web application with the goal of providing Android users with functionality similar to the incident-viewing experience available through DriveLex on iOS.

The project evolved to include:

1. A JSON incident API
2. A mobile incident interface
3. Incident filtering
4. Address geocoding
5. An interactive incident map
6. User geolocation
7. HTTPS remote access
8. Progressive Web App installation
9. Discord incident notifications

---

## 🔮 Possible Future Features

Potential future additions include:

- Push notifications
- User-selectable notification categories
- Notification preferences
- Incident history
- Improved map marker clustering
- Additional incident filters
- Traffic camera integration
- Power outage information
- Improved offline behavior
- Additional mapping tools

---

## 📄 License

No license has currently been specified.

Until a license is added, standard copyright rules apply to the source code in this repository.
