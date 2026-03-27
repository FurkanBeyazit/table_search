from fastapi import APIRouter, Query
from datetime import date, timedelta

import database
from config import (
    BHVR_TABLE, DST_TABLE, EVENT_COL, ALL_EVENTS,
    BHVR_EVNT_KND, DST_EVNT_KND,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

KR_DAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

PERIOD_DAYS = {"오늘": 0, "7일": 7, "14일": 14, "21일": 21}  # "전체" = None (no filter)


def _start(period: str):
    """기간 문자열 → 해당 날짜(단일). '전체'면 None 반환 (필터 없음)."""
    if period == "전체" or period not in PERIOD_DAYS:
        return None
    return date.today() - timedelta(days=PERIOD_DAYS[period])


# ── /api/analysis/processing ─────────────────────────────────────────────────

@router.get("/processing")
def get_processing(period: str = Query(default="전체")):
    """처리 현황: 확인/미확인 summary + event bazlı + node bazlı + günlük trend."""
    start = _start(period)
    today = date.today()

    dt_where  = "AND DATE(reg_dt) = %s::date" if start else ""
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
def get_precision(period: str = Query(default="전체")):
    """정탐 / 오탐 분析: summary + event bazlı + node bazlı + günlük trend."""
    start = _start(period)
    today = date.today()

    # date filter helpers
    dt_where  = "AND DATE(reg_dt) = %s::date" if start else ""
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


# ── /api/analysis/false_cause ─────────────────────────────────────────────────

@router.get("/false_cause")
def get_false_cause(period: str = Query(default="전체")):
    """오탐 원인(fls_pst_knd) 분析. NULL 제외, 빈 문자열('') 포함."""
    start     = _start(period)
    dt_where  = "AND DATE(reg_dt) = %s::date" if start else ""
    dt_params = [start] if start else []

    # 1. 입력 완료율 (BHAR+CALAMITY 오탐 대비 fls_pst_knd 상태 breakdown)
    comp_row = database.run_query(
        f"SELECT "
        f"  COUNT(*) AS total, "
        f"  COUNT(*) FILTER (WHERE fls_pst_knd IS NULL)  AS null_cnt, "
        f"  COUNT(*) FILTER (WHERE fls_pst_knd = '')     AS empty_cnt, "
        f"  COUNT(*) FILTER (WHERE fls_pst_knd IS NOT NULL AND fls_pst_knd != '') AS filled_cnt "
        f"FROM t_evnt_prcs_info "
        f"WHERE prcs_yn = '1' AND fls_pst_yn = '0' "
        f"AND evnt_knd IN (%s, %s) {dt_where}",
        [BHVR_EVNT_KND, DST_EVNT_KND] + dt_params,
    )
    c         = comp_row[0] if comp_row else {}
    comp_tot  = int(c.get("total",      0) or 0)
    comp_null = int(c.get("null_cnt",   0) or 0)
    comp_emp  = int(c.get("empty_cnt",  0) or 0)
    comp_fill = int(c.get("filled_cnt", 0) or 0)

    def pct(n): return round(n / comp_tot * 100, 1) if comp_tot > 0 else 0.0

    completion = {
        "total":      comp_tot,
        "filled":     comp_fill,
        "empty":      comp_emp,
        "null_cnt":   comp_null,
        "filled_pct": pct(comp_fill),
        "empty_pct":  pct(comp_emp),
        "null_pct":   pct(comp_null),
    }

    base_cond = (
        f"prcs_yn = '1' AND fls_pst_yn = '0' "
        f"AND evnt_knd IN ('{BHVR_EVNT_KND}', '{DST_EVNT_KND}') "
        f"AND fls_pst_knd IS NOT NULL {dt_where}"
    )

    # 2. 원인별 합계 (NULL 제외, '' 포함)
    cause_rows = database.run_query(
        f"SELECT fls_pst_knd AS cause, COUNT(*) AS cnt "
        f"FROM t_evnt_prcs_info "
        f"WHERE {base_cond} "
        f"GROUP BY fls_pst_knd ORDER BY cnt DESC",
        dt_params,
    )
    all_causes   = [r["cause"] for r in cause_rows]
    cause_totals = {r["cause"]: int(r["cnt"]) for r in cause_rows}
    total        = sum(cause_totals.values())

    causes = [
        {
            "cause": c,
            "cnt":   cause_totals[c],
            "rate":  round(cause_totals[c] / total * 100, 1) if total > 0 else 0.0,
        }
        for c in all_causes
    ]

    # 3. 이벤트별 원인 분포
    def ev_cause_query(table, knd):
        return database.run_query(
            f"SELECT b.{EVENT_COL} AS et, e.fls_pst_knd AS cause, COUNT(*) AS cnt "
            f"FROM t_evnt_prcs_info e "
            f"JOIN (SELECT DISTINCT ON (seq) seq, {EVENT_COL} FROM {table} ORDER BY seq) b "
            f"  ON b.seq = e.evnt_seq "
            f"WHERE e.evnt_knd = %s AND e.prcs_yn = '1' AND e.fls_pst_yn = '0' "
            f"AND e.fls_pst_knd IS NOT NULL {dt_where} "
            f"GROUP BY b.{EVENT_COL}, e.fls_pst_knd",
            [knd] + dt_params,
        )

    ev_map = {}
    for r in ev_cause_query(BHVR_TABLE, BHVR_EVNT_KND) + ev_cause_query(DST_TABLE, DST_EVNT_KND):
        ev_map.setdefault(r["et"], {})
        ev_map[r["et"]][r["cause"]] = ev_map[r["et"]].get(r["cause"], 0) + int(r["cnt"])

    events = [
        {"event": ev, "cause_counts": ev_map[ev], "total": sum(ev_map[ev].values())}
        for ev in ALL_EVENTS if ev in ev_map
    ]

    # 3. 사용자별 원인 분포
    user_rows = database.run_query(
        f"SELECT COALESCE(reg_id, '미확인') AS reg_id, "
        f"  fls_pst_knd AS cause, COUNT(*) AS cnt "
        f"FROM t_evnt_prcs_info "
        f"WHERE {base_cond} "
        f"GROUP BY COALESCE(reg_id, '미확인'), fls_pst_knd",
        dt_params,
    )

    user_map = {}
    for r in user_rows:
        uid = r["reg_id"]
        user_map.setdefault(uid, {})
        user_map[uid][r["cause"]] = user_map[uid].get(r["cause"], 0) + int(r["cnt"])

    users = sorted(
        [{"reg_id": uid, "cause_counts": cc, "total": sum(cc.values())}
         for uid, cc in user_map.items()],
        key=lambda x: -x["total"],
    )

    return {
        "period":     period,
        "completion": completion,
        "all_causes": all_causes,
        "total":      total,
        "causes":     causes,
        "events":     events,
        "users":      users,
    }


# ── /api/analysis/time_dist ───────────────────────────────────────────────────

@router.get("/time_dist")
def get_time_dist(period: str = Query(default="전체")):
    """시간대별 오탐 분析: 카드 + heatmap + 시간대 bar + 시간별 line."""
    start     = _start(period)
    dt_where  = "AND DATE(reg_dt) = %s::date" if start else ""
    dt_params = [start] if start else []

    base_filter = (
        f"e.prcs_yn = '1' AND e.fls_pst_yn = '0' "
        f"AND e.evnt_knd IN ('{BHVR_EVNT_KND}', '{DST_EVNT_KND}') {dt_where}"
    )

    # 1. 시간별 총계 (line + cards + slot bar 용)
    hour_rows = database.run_query(
        f"SELECT EXTRACT(HOUR FROM reg_dt)::int AS hr, COUNT(*) AS cnt "
        f"FROM t_evnt_prcs_info e "
        f"WHERE {base_filter} AND reg_dt IS NOT NULL "
        f"GROUP BY hr ORDER BY hr",
        dt_params,
    )
    hour_map   = {int(r["hr"]): int(r["cnt"]) for r in hour_rows if r["hr"] is not None}
    total      = sum(hour_map.values())
    hour_total = [{"hour": h, "count": hour_map.get(h, 0)} for h in range(24)]

    # cards
    if hour_map:
        busiest_hr  = max(hour_map, key=hour_map.get)
        quietest_hr = min(hour_map, key=hour_map.get)
    else:
        busiest_hr = quietest_hr = 0

    night_cnt = sum(hour_map.get(h, 0) for h in range(0,  6))
    day_cnt   = sum(hour_map.get(h, 0) for h in range(6, 18))
    eve_cnt   = sum(hour_map.get(h, 0) for h in range(18, 24))

    def pct(n): return round(n / total * 100, 1) if total > 0 else 0.0

    cards = {
        "busiest_hr":    busiest_hr,
        "busiest_cnt":   hour_map.get(busiest_hr, 0),
        "quietest_hr":   quietest_hr,
        "quietest_cnt":  hour_map.get(quietest_hr, 0),
        "night_rate":    pct(night_cnt),   # 00-06
        "day_rate":      pct(day_cnt),     # 06-18
        "total":         total,
    }

    # slots bar
    slots = [
        {"label": "야간 00-06", "count": night_cnt},
        {"label": "오전 06-12", "count": sum(hour_map.get(h, 0) for h in range(6,  12))},
        {"label": "오후 12-18", "count": sum(hour_map.get(h, 0) for h in range(12, 18))},
        {"label": "저녁 18-24", "count": eve_cnt},
    ]

    # 2. 이벤트 × 시간 heatmap
    def ev_hour_query(table, knd):
        return database.run_query(
            f"SELECT EXTRACT(HOUR FROM e.reg_dt)::int AS hr, "
            f"  b.{EVENT_COL} AS et, COUNT(*) AS cnt "
            f"FROM t_evnt_prcs_info e "
            f"JOIN (SELECT DISTINCT ON (seq) seq, {EVENT_COL} FROM {table} ORDER BY seq) b "
            f"  ON b.seq = e.evnt_seq "
            f"WHERE e.evnt_knd = %s AND e.prcs_yn = '1' AND e.fls_pst_yn = '0' "
            f"AND e.reg_dt IS NOT NULL {dt_where} "
            f"GROUP BY hr, b.{EVENT_COL}",
            [knd] + dt_params,
        )

    ev_hour = {}  # {event: {hour: count}}
    for r in ev_hour_query(BHVR_TABLE, BHVR_EVNT_KND) + ev_hour_query(DST_TABLE, DST_EVNT_KND):
        if r["hr"] is None:
            continue
        ev_hour.setdefault(r["et"], {})
        ev_hour[r["et"]][int(r["hr"])] = int(r["cnt"])

    hourly_events = {
        ev: [ev_hour.get(ev, {}).get(h, 0) for h in range(24)]
        for ev in ALL_EVENTS
    }

    return {
        "period":        period,
        "cards":         cards,
        "hour_total":    hour_total,
        "slots":         slots,
        "hourly_events": hourly_events,
    }
