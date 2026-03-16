# Security Analytics Platform

CCTV event analytics platform built with FastAPI and Gradio.
Queries behavior and disaster events from PostgreSQL and displays stats, record lists, and per-node breakdowns.

## Structure

```
├── config.ini          # Settings (DB, paths, events) — not committed
├── config.py           # Reads config.ini
├── database.py         # PostgreSQL query helper
├── main.py             # FastAPI app
├── routers/
│   └── search.py       # Search endpoints
├── ui.py               # Gradio UI
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

Copy `config.ini.example` to `config.ini` and fill in your values.

## Run

```bash
# Terminal 1 — API
python main.py        # http://localhost:8000

# Terminal 2 — UI
python ui.py          # http://localhost:7860
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search/stats` | Event counts grouped by type |
| GET | `/api/search/list` | Record list (max 100, newest first) |
| GET | `/api/search/node-stats` | Total events per node/channel |
| GET | `/api/search/node-detail` | Event breakdown for a specific node |

All endpoints accept: `start_dt`, `end_dt`, `events[]`

## Config

Edit `config.ini` to change database connection, image path mount letter, or event lists.

```ini
[database]
url = postgresql://user:pass@host:port/dbname

[path]
linux_prefix  = /root/BestShot/
windows_drive = Z
```
