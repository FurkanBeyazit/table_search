from fastapi import APIRouter, Query
from typing import List
from datetime import datetime, timedelta

import database
from config import (
    BHVR_TABLE, DST_TABLE, EVENT_COL,
    BHVR_EVENTS, DST_EVENTS, ALL_EVENTS,
    LINUX_PATH_PREFIX, WINDOWS_MOUNT_LETTER,
)

router = APIRouter(prefix="/api/search", tags=["search"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def img_to_file_url(img_path: str) -> str:
    """Convert Linux image path → browser-friendly file:// URL for Windows mount."""
    if not img_path:
        return ""
    rel = img_path.replace(LINUX_PATH_PREFIX, "").lstrip("/")
    rel = rel.replace("\\", "/")
    return f"file:///{WINDOWS_MOUNT_LETTER}:/{rel}"


def parse_dtct_dt(val) -> str:
    """Parse dtct_dt (stored as YYYYMMDDHHmmss UTC) and add 9 h → KST string."""
    if not val:
        return ""
    try:
        dt = datetime.strptime(str(val).strip(), "%Y%m%d%H%M%S")
        return (dt + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(val)


def build_base_sql(events: List[str], start_dt: str, end_dt: str):
    """
    Build a UNION ALL query over t_bhvr_anly and/or t_dst_anly
    depending on which event types are requested.
    Returns (sql_string, params_list).
    """
    bhvr = [e for e in events if e in BHVR_EVENTS]
    dst  = [e for e in events if e in DST_EVENTS]
    parts, params = [], []

    if bhvr:
        ph = ", ".join(["%s"] * len(bhvr))
        parts.append(
            f"SELECT node_id, ch, reg_dt, dtct_dt, img_path, {EVENT_COL} AS event_type "
            f"FROM {BHVR_TABLE} "
            f"WHERE reg_dt BETWEEN %s AND %s AND {EVENT_COL} IN ({ph})"
        )
        params += [start_dt, end_dt] + bhvr

    if dst:
        ph = ", ".join(["%s"] * len(dst))
        parts.append(
            f"SELECT node_id, ch, reg_dt, dtct_dt, img_path, {EVENT_COL} AS event_type "
            f"FROM {DST_TABLE} "
            f"WHERE reg_dt BETWEEN %s AND %s AND {EVENT_COL} IN ({ph})"
        )
        params += [start_dt, end_dt] + dst

    if not parts:
        return None, []

    return " UNION ALL ".join(parts), params


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    start_dt: str,
    end_dt: str,
    events: List[str] = Query(default=ALL_EVENTS),
):
    """Event counts grouped by type for the given time range."""
    base, params = build_base_sql(events, start_dt, end_dt)
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
):
    """Detailed record list (max 100 rows, newest first)."""
    base, params = build_base_sql(events, start_dt, end_dt)
    if not base:
        return {"records": []}

    sql = f"SELECT * FROM ({base}) t ORDER BY reg_dt DESC LIMIT 100"
    rows = database.run_query(sql, params)
    return {
        "records": [
            {
                "node_id": r["node_id"],
                "ch":      r["ch"],
                "reg_dt":  str(r["reg_dt"]),
                "dtct_dt": parse_dtct_dt(r.get("dtct_dt")),
                "event":   r["event_type"],
                "img_url": img_to_file_url(r.get("img_path", "")),
            }
            for r in rows
        ]
    }


@router.get("/node-stats")
def get_node_stats(
    start_dt: str,
    end_dt: str,
    events: List[str] = Query(default=ALL_EVENTS),
):
    """Total event count per node / channel."""
    base, params = build_base_sql(events, start_dt, end_dt)
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
    """Event breakdown for a specific node + channel."""
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
