from fastapi import APIRouter, Query
from datetime import date, timedelta

import database
from config import (
    BHVR_TABLE, DST_TABLE, EVENT_COL, ALL_EVENTS,
    BHVR_EVNT_KND, DST_EVNT_KND,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

KR_DAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

PERIOD_DAYS = {"오늘": 0, "7일": 6, "14일": 13, "21일": 20}  # "전체" = None (no filter)


def _start(period: str):
    """기간 문자열 → 시작 date. '전체'면 None 반환 (필터 없음)."""
    if period == "전체" or period not in PERIOD_DAYS:
        return None
    return date.today() - timedelta(days=PERIOD_DAYS[period])


# ── /api/analysis/processing ─────────────────────────────────────────────────

@router.get("/processing")
def get_processing(period: str = Query(default="전체")):
    """처리 현황: 확인/미확인 summary + event bazlı + node bazlı + günlük trend."""
    start = _start(period)
    today = date.today()

    dt_where  = "AND reg_dt >= %s::date" if start else ""
    dt_params = [start] if start else []

    # 1. Summary ────────────────────────────────────────────────────────────
    s = database.run_query(
        f"SELECT "
        f"  COUNT(*) AS total, "
        f"  COUNT(*) FILTER (WHERE prcs_yn = '1') AS processed, "
        f"  COUNT(*) FILTER (WHERE prcs_yn = '0') AS unprocessed "
        f"FROM t_evnt_prcs_info "
        f"WHERE prcs_yn IS NOT NULL {dt_where}",
        dt_params,
    )
    row  = s[0] if s else {}
    tot  = int(row.get("total",       0) or 0)
    proc = int(row.get("processed",   0) or 0)
    unpr = int(row.get("unprocessed", 0) or 0)
    rate = round(proc / tot * 100, 1) if tot > 0 else 0.0

    summary = {"total": tot, "processed": proc, "unprocessed": unpr, "rate": rate}

    # 2. Event bazlı ────────────────────────────────────────────────────────
    def ev_query(table, knd):
        return database.run_query(
            f"SELECT b.{EVENT_COL} AS et, "
            f"  COUNT(*) AS total, "
            f"  COUNT(*) FILTER (WHERE e.prcs_yn = '1') AS processed, "
            f"  COUNT(*) FILTER (WHERE e.prcs_yn = '0') AS unprocessed "
            f"FROM t_evnt_prcs_info e "
            f"JOIN (SELECT DISTINCT ON (seq) seq, {EVENT_COL} FROM {table} ORDER BY seq) b "
            f"  ON b.seq = e.evnt_seq "
            f"WHERE e.evnt_knd = %s AND e.prcs_yn IS NOT NULL {dt_where} "
            f"GROUP BY b.{EVENT_COL}",
            [knd] + dt_params,
        )

    ev_map = {}
    for r in ev_query(BHVR_TABLE, BHVR_EVNT_KND) + ev_query(DST_TABLE, DST_EVNT_KND):
        t = int(r["total"]       or 0)
        p = int(r["processed"]   or 0)
        u = int(r["unprocessed"] or 0)
        ev_map[r["et"]] = {
            "processed":   p,
            "unprocessed": u,
            "total":       t,
            "unpr_rate":   round(u / t * 100, 1) if t > 0 else 0.0,
        }

    empty_ev = {"processed": 0, "unprocessed": 0, "total": 0, "unpr_rate": 0.0}
    events = [{"event": ev, **ev_map.get(ev, empty_ev)} for ev in ALL_EVENTS]

    # 3. Node bazlı ─────────────────────────────────────────────────────────
    def node_query(table, knd):
        return database.run_query(
            f"SELECT CAST(b.node_id AS TEXT) AS node_id, CAST(b.ch AS TEXT) AS ch, "
            f"  COUNT(*) AS total, "
            f"  COUNT(*) FILTER (WHERE e.prcs_yn = '1') AS processed, "
            f"  COUNT(*) FILTER (WHERE e.prcs_yn = '0') AS unprocessed "
            f"FROM t_evnt_prcs_info e "
            f"JOIN (SELECT DISTINCT ON (seq) seq, node_id, ch FROM {table} ORDER BY seq) b "
            f"  ON b.seq = e.evnt_seq "
            f"WHERE e.evnt_knd = %s AND e.prcs_yn IS NOT NULL {dt_where} "
            f"GROUP BY b.node_id, b.ch",
            [knd] + dt_params,
        )

    node_map = {}
    for r in node_query(BHVR_TABLE, BHVR_EVNT_KND) + node_query(DST_TABLE, DST_EVNT_KND):
        key = (r["node_id"], r["ch"])
        if key not in node_map:
            node_map[key] = {"processed": 0, "unprocessed": 0, "total": 0}
        node_map[key]["processed"]   += int(r["processed"]   or 0)
        node_map[key]["unprocessed"] += int(r["unprocessed"] or 0)
        node_map[key]["total"]       += int(r["total"]       or 0)

    name_map = {}
    if node_map:
        ids = list({k[0] for k in node_map})
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

    nodes = []
    for (nid, ch), v in sorted(node_map.items(), key=lambda x: -x[1]["unprocessed"]):
        t = v["total"]
        nodes.append({
            "node_id":     nid,
            "node_name":   name_map.get(nid, ""),
            "ch":          ch,
            "processed":   v["processed"],
            "unprocessed": v["unprocessed"],
            "total":       t,
            "unpr_rate":   round(v["unprocessed"] / t * 100, 1) if t > 0 else 0.0,
        })

    # 4. Günlük trend ───────────────────────────────────────────────────────
    daily_rows = database.run_query(
        f"SELECT DATE(reg_dt) AS day, "
        f"  COUNT(*) AS total, "
        f"  COUNT(*) FILTER (WHERE prcs_yn = '1') AS processed, "
        f"  COUNT(*) FILTER (WHERE prcs_yn = '0') AS unprocessed "
        f"FROM t_evnt_prcs_info "
        f"WHERE 1=1 {dt_where} "
        f"GROUP BY DATE(reg_dt) ORDER BY day",
        dt_params,
    )
    daily_map = {str(r["day"]): r for r in daily_rows}

    if start is None:
        actual_start = (date.fromisoformat(min(daily_map.keys()))
                        if daily_map else today)
    else:
        actual_start = start
    days_count = (today - actual_start).days + 1

    daily = []
    for i in range(days_count):
        d  = actual_start + timedelta(days=i)
        ds = str(d)
        r  = daily_map.get(ds, {})
        t  = int(r.get("total",       0) or 0)
        p  = int(r.get("processed",   0) or 0)
        u  = int(r.get("unprocessed", 0) or 0)
        daily.append({
            "date":        ds,
            "label":       KR_DAYS[d.weekday()],
            "processed":   p,
            "unprocessed": u,
            "total":       t,
            "unpr_rate":   round(u / t * 100, 1) if t > 0 else 0.0,
        })

    return {
        "period":  period,
        "summary": summary,
        "events":  events,
        "nodes":   nodes,
        "daily":   daily,
    }


# ── /api/analysis/precision ───────────────────────────────────────────────────

@router.get("/precision")
def get_precision(period: str = Query(default="14일")):
    """정탐 / 오탐 분析: summary + event bazlı + node bazlı + günlük trend."""
    start = _start(period)
    today = date.today()

    # date filter helpers
    dt_where  = "AND reg_dt >= %s::date" if start else ""
    dt_params = [start] if start else []

    # 1. Summary ────────────────────────────────────────────────────────────
    s = database.run_query(
        f"SELECT "
        f"  COUNT(*) AS total, "
        f"  COUNT(*) FILTER (WHERE fls_pst_yn = '1') AS jeongdam, "
        f"  COUNT(*) FILTER (WHERE fls_pst_yn = '0') AS odam "
        f"FROM t_evnt_prcs_info "
        f"WHERE prcs_yn = '1' {dt_where}",
        dt_params,
    )
    row   = s[0] if s else {}
    total = int(row.get("total",    0) or 0)
    jd    = int(row.get("jeongdam", 0) or 0)
    od    = int(row.get("odam",     0) or 0)
    prec  = round(jd / total * 100, 1) if total > 0 else 0.0

    summary = {"total": total, "jeongdam": jd, "odam": od, "precision": prec}

    # 2. Event bazlı ────────────────────────────────────────────────────────
    def ev_query(table, knd):
        return database.run_query(
            f"SELECT b.{EVENT_COL} AS et, "
            f"  COUNT(*) AS total, "
            f"  COUNT(*) FILTER (WHERE e.fls_pst_yn = '1') AS jeongdam, "
            f"  COUNT(*) FILTER (WHERE e.fls_pst_yn = '0') AS odam "
            f"FROM t_evnt_prcs_info e "
            f"JOIN (SELECT DISTINCT ON (seq) seq, {EVENT_COL} FROM {table} ORDER BY seq) b "
            f"  ON b.seq = e.evnt_seq "
            f"WHERE e.evnt_knd = %s AND e.prcs_yn = '1' {dt_where} "
            f"GROUP BY b.{EVENT_COL}",
            [knd] + dt_params,
        )

    ev_map = {}
    for r in ev_query(BHVR_TABLE, BHVR_EVNT_KND) + ev_query(DST_TABLE, DST_EVNT_KND):
        t = int(r["total"]    or 0)
        j = int(r["jeongdam"] or 0)
        o = int(r["odam"]     or 0)
        ev_map[r["et"]] = {
            "jeongdam":  j,
            "odam":      o,
            "total":     t,
            "odam_rate": round(o / t * 100, 1) if t > 0 else 0.0,
        }

    empty_ev = {"jeongdam": 0, "odam": 0, "total": 0, "odam_rate": 0.0}
    events = [{"event": ev, **ev_map.get(ev, empty_ev)} for ev in ALL_EVENTS]

    # 3. Node bazlı ─────────────────────────────────────────────────────────
    def node_query(table, knd):
        return database.run_query(
            f"SELECT CAST(b.node_id AS TEXT) AS node_id, CAST(b.ch AS TEXT) AS ch, "
            f"  COUNT(*) AS total, "
            f"  COUNT(*) FILTER (WHERE e.fls_pst_yn = '1') AS jeongdam, "
            f"  COUNT(*) FILTER (WHERE e.fls_pst_yn = '0') AS odam "
            f"FROM t_evnt_prcs_info e "
            f"JOIN (SELECT DISTINCT ON (seq) seq, node_id, ch FROM {table} ORDER BY seq) b "
            f"  ON b.seq = e.evnt_seq "
            f"WHERE e.evnt_knd = %s AND e.prcs_yn = '1' {dt_where} "
            f"GROUP BY b.node_id, b.ch",
            [knd] + dt_params,
        )

    node_map = {}
    for r in node_query(BHVR_TABLE, BHVR_EVNT_KND) + node_query(DST_TABLE, DST_EVNT_KND):
        key = (r["node_id"], r["ch"])
        if key not in node_map:
            node_map[key] = {"jeongdam": 0, "odam": 0, "total": 0}
        node_map[key]["jeongdam"] += int(r["jeongdam"] or 0)
        node_map[key]["odam"]     += int(r["odam"]     or 0)
        node_map[key]["total"]    += int(r["total"]    or 0)

    name_map = {}
    if node_map:
        ids = list({k[0] for k in node_map})
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

    nodes = []
    for (nid, ch), v in sorted(node_map.items(), key=lambda x: -x[1]["odam"]):
        t = v["total"]
        nodes.append({
            "node_id":   nid,
            "node_name": name_map.get(nid, ""),
            "ch":        ch,
            "jeongdam":  v["jeongdam"],
            "odam":      v["odam"],
            "total":     t,
            "odam_rate": round(v["odam"] / t * 100, 1) if t > 0 else 0.0,
        })

    # 4. Günlük trend ───────────────────────────────────────────────────────
    daily_rows = database.run_query(
        f"SELECT DATE(reg_dt) AS day, "
        f"  COUNT(*) FILTER (WHERE fls_pst_yn = '1') AS jeongdam, "
        f"  COUNT(*) FILTER (WHERE fls_pst_yn = '0') AS odam, "
        f"  COUNT(*) AS total "
        f"FROM t_evnt_prcs_info "
        f"WHERE prcs_yn = '1' {dt_where} "
        f"GROUP BY DATE(reg_dt) ORDER BY day",
        dt_params,
    )
    daily_map = {str(r["day"]): r for r in daily_rows}

    # 전체 seçeneğinde verinin ilk gününden bugüne kadar
    if start is None:
        actual_start = (date.fromisoformat(min(daily_map.keys()))
                        if daily_map else today)
    else:
        actual_start = start
    days_count = (today - actual_start).days + 1
    daily = []
    for i in range(days_count):
        d  = actual_start + timedelta(days=i)
        ds = str(d)
        r  = daily_map.get(ds, {})
        t  = int(r.get("total",    0) or 0)
        j  = int(r.get("jeongdam", 0) or 0)
        o  = int(r.get("odam",     0) or 0)
        daily.append({
            "date":      ds,
            "label":     KR_DAYS[d.weekday()],
            "jeongdam":  j,
            "odam":      o,
            "total":     t,
            "odam_rate": round(o / t * 100, 1) if t > 0 else 0.0,
        })

    return {
        "period":  period,
        "summary": summary,
        "events":  events,
        "nodes":   nodes,
        "daily":   daily,
    }
