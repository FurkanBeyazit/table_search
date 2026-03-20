import os
import io
from urllib.parse import quote
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import List
from datetime import datetime, timedelta

import database
from config import (
    BHVR_TABLE, DST_TABLE, EVENT_COL,
    BHVR_EVENTS, DST_EVENTS, ALL_EVENTS,
    LINUX_PATH_PREFIX, WINDOWS_MOUNT_LETTER, API_BASE_URL,
)

router = APIRouter(prefix="/api/search", tags=["search"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_dt_param(s: str) -> str:
    """Accept both '20260316111320' (14-digit) and '2026-03-16 11:13:20' formats."""
    s = s.strip()
    if len(s) == 14 and s.isdigit():
        return datetime.strptime(s, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    return s


def linux_to_win(img_path: str) -> str:
    """Convert Linux path to Windows path string."""
    win = img_path.replace(LINUX_PATH_PREFIX, f"{WINDOWS_MOUNT_LETTER}:\\")
    return win.replace("/", "\\")


def img_to_api_url(img_path: str) -> str:
    if not img_path:
        return ""
    return f"{API_BASE_URL}/api/search/image?path={quote(img_path)}"


def img_to_thumb_url(img_path: str) -> str:
    if not img_path:
        return ""
    return f"{API_BASE_URL}/api/search/thumbnail?path={quote(img_path)}"


def parse_dtct_dt(val) -> str:
    if not val:
        return ""
    try:
        dt = datetime.strptime(str(val).strip(), "%Y%m%d%H%M%S")
        return (dt + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(val)


def build_base_sql(events: List[str], start_dt: str, end_dt: str, node_ids: List[str] = None):
    bhvr = [e for e in events if e in BHVR_EVENTS]
    dst  = [e for e in events if e in DST_EVENTS]
    parts, params = [], []

    node_clause = ""
    node_params = []
    if node_ids:
        ph = ", ".join(["%s"] * len(node_ids))
        node_clause = f" AND CAST(node_id AS TEXT) IN ({ph})"
        node_params = node_ids

    if bhvr:
        ph = ", ".join(["%s"] * len(bhvr))
        parts.append(
            f"SELECT node_id, ch, reg_dt, dtct_dt, img_path, {EVENT_COL} AS event_type "
            f"FROM {BHVR_TABLE} "
            f"WHERE reg_dt BETWEEN %s AND %s AND {EVENT_COL} IN ({ph}){node_clause}"
        )
        params += [start_dt, end_dt] + bhvr + node_params

    if dst:
        ph = ", ".join(["%s"] * len(dst))
        parts.append(
            f"SELECT node_id, ch, reg_dt, dtct_dt, img_path, {EVENT_COL} AS event_type "
            f"FROM {DST_TABLE} "
            f"WHERE reg_dt BETWEEN %s AND %s AND {EVENT_COL} IN ({ph}){node_clause}"
        )
        params += [start_dt, end_dt] + dst + node_params

    if not parts:
        return None, []

    return " UNION ALL ".join(parts), params


# ── Image endpoints ───────────────────────────────────────────────────────────

@router.get("/image")
def get_image(path: str):
    """Full-size image served over HTTP."""
    win_path = linux_to_win(path)
    if not os.path.isfile(win_path):
        raise HTTPException(status_code=404, detail=f"Not found: {win_path}")
    return FileResponse(win_path)


@router.get("/thumbnail")
def get_thumbnail(path: str):
    """Resized thumbnail (120×90, JPEG q50) with browser cache."""
    try:
        from PIL import Image
    except ImportError:
        raise HTTPException(status_code=500, detail="Pillow not installed")

    win_path = linux_to_win(path)
    if not os.path.isfile(win_path):
        raise HTTPException(status_code=404, detail=f"Not found: {win_path}")

    img = Image.open(win_path)
    img.thumbnail((120, 90), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=50)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ── Search endpoints ──────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    start_dt: str,
    end_dt: str,
    events: List[str] = Query(default=ALL_EVENTS),
    node_ids: List[str] = Query(default=None, alias="node_id"),
):
    start_dt, end_dt = parse_dt_param(start_dt), parse_dt_param(end_dt)
    base, params = build_base_sql(events, start_dt, end_dt, node_ids or [])
    if not base:
        return {"time_range": {"start": start_dt, "end": end_dt}, "events": []}

    sql = (
        f"SELECT event_type, COUNT(*) AS cnt "
        f"FROM ({base}) t "
        f"GROUP BY event_type ORDER BY cnt DESC"
    )
    rows = database.run_query(sql, params)
    return {
        "time_range": {"start": start_dt, "end": end_dt},
        "events": [{"event": r["event_type"], "count": r["cnt"]} for r in rows],
    }


@router.get("/list")
def get_list(
    start_dt: str,
    end_dt: str,
    events: List[str] = Query(default=ALL_EVENTS),
    node_ids: List[str] = Query(default=None, alias="node_id"),
):
    start_dt, end_dt = parse_dt_param(start_dt), parse_dt_param(end_dt)
    base, params = build_base_sql(events, start_dt, end_dt, node_ids or [])
    if not base:
        return {"records": []}

    sql = f"SELECT * FROM ({base}) t ORDER BY reg_dt DESC LIMIT 100"
    rows = database.run_query(sql, params)

    # node_id → name lookup from t_viewer_node
    name_map = {}
    if rows:
        ids = list({str(r["node_id"]) for r in rows})
        ph  = ",".join(["%s"] * len(ids))
        try:
            name_rows = database.run_query(
                f"SELECT DISTINCT ON (CAST(node_id AS TEXT)) "
                f"CAST(node_id AS TEXT) AS nid, name "
                f"FROM t_viewer_node WHERE CAST(node_id AS TEXT) IN ({ph})",
                ids,
            )
            name_map = {r["nid"]: r["name"] for r in name_rows}
        except Exception:
            pass

    return {
        "records": [
            {
                "node_id":   r["node_id"],
                "node_name": name_map.get(str(r["node_id"]), ""),
                "ch":        r["ch"],
                "dtct_dt":   parse_dtct_dt(r.get("dtct_dt")),
                "event":     r["event_type"],
                "img_url":   img_to_api_url(r.get("img_path", "")),
                "thumb_url": img_to_thumb_url(r.get("img_path", "")),
            }
            for r in rows
        ]
    }


@router.get("/node-stats")
def get_node_stats(
    start_dt: str,
    end_dt: str,
    events: List[str] = Query(default=ALL_EVENTS),
    node_ids: List[str] = Query(default=None, alias="node_id"),
):
    start_dt, end_dt = parse_dt_param(start_dt), parse_dt_param(end_dt)
    base, params = build_base_sql(events, start_dt, end_dt, node_ids or [])
    if not base:
        return {"nodes": []}

    sql = (
        f"SELECT node_id, ch, COUNT(*) AS total "
        f"FROM ({base}) t "
        f"GROUP BY node_id, ch ORDER BY total DESC"
    )
    rows = database.run_query(sql, params)
    return {
        "nodes": [{"node_id": r["node_id"], "ch": r["ch"], "total": r["total"]} for r in rows]
    }


@router.get("/node-detail")
def get_node_detail(
    node_id: str,
    ch: str,
    start_dt: str,
    end_dt: str,
    events: List[str] = Query(default=ALL_EVENTS),
):
    start_dt, end_dt = parse_dt_param(start_dt), parse_dt_param(end_dt)
    base, params = build_base_sql(events, start_dt, end_dt)
    if not base:
        return {"node_id": node_id, "ch": ch, "events": []}

    sql = (
        f"SELECT event_type, COUNT(*) AS cnt "
        f"FROM ({base}) t "
        f"WHERE CAST(node_id AS TEXT) = %s AND CAST(ch AS TEXT) = %s "
        f"GROUP BY event_type ORDER BY cnt DESC"
    )
    rows = database.run_query(sql, params + [node_id, ch])
    return {
        "node_id": node_id,
        "ch": ch,
        "events": [{"event": r["event_type"], "count": r["cnt"]} for r in rows],
    }
