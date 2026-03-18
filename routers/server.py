import io
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from datetime import date, timedelta

import database
from config import BHVR_TABLE, DST_TABLE, EVENT_COL, ALL_EVENTS

router = APIRouter(prefix="/api/server", tags=["server"])


class NodeItem(BaseModel):
    viewer_name:     str
    node_id:         str
    management_code: str = ""
    name:            str = ""


@router.get("/nodes")
def get_nodes():
    rows = database.run_query(
        "SELECT id, viewer_name, node_id, management_code, name "
        "FROM t_viewer_node ORDER BY viewer_name, node_id"
    )
    return {"nodes": rows}


@router.post("/nodes")
def add_node(item: NodeItem):
    database.run_execute(
        "INSERT INTO t_viewer_node (viewer_name, node_id, management_code, name) "
        "VALUES (%s, %s, %s, %s)",
        [item.viewer_name, item.node_id, item.management_code, item.name],
    )
    return {"ok": True}


@router.delete("/nodes/{row_id}")
def delete_node(row_id: int):
    database.run_execute("DELETE FROM t_viewer_node WHERE id = %s", [row_id])
    return {"ok": True}


@router.post("/import")
async def import_excel(file: UploadFile = File(...)):
    import pandas as pd

    content = await file.read()
    df = pd.read_excel(io.BytesIO(content), skiprows=2)

    needed = ["Viewer Name", "NodeID", "ManagementCode", "Name"]
    df = df[[c for c in needed if c in df.columns]]
    df = df.dropna(subset=["Viewer Name", "NodeID"])

    stmts = [("DELETE FROM t_viewer_node", None)]
    for _, row in df.iterrows():
        stmts.append((
            "INSERT INTO t_viewer_node (viewer_name, node_id, management_code, name) "
            "VALUES (%s, %s, %s, %s)",
            [
                str(row.get("Viewer Name", "")),
                str(row.get("NodeID", "")),
                str(row["ManagementCode"]) if "ManagementCode" in row.index and str(row["ManagementCode"]) != "nan" else "",
                str(row["Name"])           if "Name"           in row.index and str(row["Name"])           != "nan" else "",
            ],
        ))
    database.run_transaction(stmts)

    return {"imported": len(df)}


@router.get("/stats")
def get_server_stats():
    today = date.today()

    viewers = database.run_query(
        "SELECT DISTINCT viewer_name FROM t_viewer_node ORDER BY viewer_name"
    )
    if not viewers:
        return {"viewers": [], "events": ALL_EVENTS}

    # 14일 event 건수 (bhvr + dst)
    bhvr_ev = database.run_query(
        f"SELECT vn.viewer_name, b.{EVENT_COL} AS et, COUNT(*) AS cnt "
        f"FROM t_viewer_node vn "
        f"JOIN {BHVR_TABLE} b ON b.node_id = vn.node_id "
        f"WHERE b.reg_dt >= %s::date - INTERVAL '14 days' "
        f"GROUP BY vn.viewer_name, b.{EVENT_COL}",
        [today],
    )
    dst_ev = database.run_query(
        f"SELECT vn.viewer_name, d.{EVENT_COL} AS et, COUNT(*) AS cnt "
        f"FROM t_viewer_node vn "
        f"JOIN {DST_TABLE} d ON d.node_id = vn.node_id "
        f"WHERE d.reg_dt >= %s::date - INTERVAL '14 days' "
        f"GROUP BY vn.viewer_name, d.{EVENT_COL}",
        [today],
    )

    ev_map = {}
    for r in bhvr_ev + dst_ev:
        v = r["viewer_name"]
        if v not in ev_map:
            ev_map[v] = {}
        ev_map[v][r["et"]] = ev_map[v].get(r["et"], 0) + int(r["cnt"])

    # 14일 일별 event 상세 (viewer + day + event bazlı)
    bhvr_daily = database.run_query(
        f"SELECT vn.viewer_name, DATE(b.reg_dt) AS day, b.{EVENT_COL} AS et, COUNT(*) AS cnt "
        f"FROM t_viewer_node vn "
        f"JOIN {BHVR_TABLE} b ON b.node_id = vn.node_id "
        f"WHERE b.reg_dt >= %s::date - INTERVAL '14 days' "
        f"GROUP BY vn.viewer_name, DATE(b.reg_dt), b.{EVENT_COL}",
        [today],
    )
    dst_daily = database.run_query(
        f"SELECT vn.viewer_name, DATE(d.reg_dt) AS day, d.{EVENT_COL} AS et, COUNT(*) AS cnt "
        f"FROM t_viewer_node vn "
        f"JOIN {DST_TABLE} d ON d.node_id = vn.node_id "
        f"WHERE d.reg_dt >= %s::date - INTERVAL '14 days' "
        f"GROUP BY vn.viewer_name, DATE(d.reg_dt), d.{EVENT_COL}",
        [today],
    )

    # {viewer: {date: {event: cnt}}}
    daily_map = {}
    for r in bhvr_daily + dst_daily:
        v  = r["viewer_name"]
        ds = str(r["day"])
        et = r["et"]
        if v  not in daily_map: daily_map[v]     = {}
        if ds not in daily_map[v]: daily_map[v][ds] = {}
        daily_map[v][ds][et] = daily_map[v][ds].get(et, 0) + int(r["cnt"])

    dates_14 = [str(today - timedelta(days=13 - i)) for i in range(14)]

    result = []
    for v_row in viewers:
        v     = v_row["viewer_name"]
        ev    = ev_map.get(v, {})
        total = sum(ev.values())
        daily = []
        for d in dates_14:
            row = {"date": d}
            for e in ALL_EVENTS:
                row[e] = daily_map.get(v, {}).get(d, {}).get(e, 0)
            daily.append(row)
        result.append({
            "viewer_name": v,
            "events":      {e: ev.get(e, 0) for e in ALL_EVENTS},
            "total":       total,
            "daily":       daily,
        })

    return {"viewers": result, "events": ALL_EVENTS}
