from fastapi import APIRouter, Query
from datetime import date, datetime, timedelta

import database
from config import BHVR_TABLE, DST_TABLE, EVENT_COL, ALL_EVENTS, BHVR_EVENTS, DST_EVENTS

router = APIRouter(prefix="/api/stats", tags=["stats"])

KR_DAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}


@router.get("/today")
def get_today():
    """오늘 / 7일 / 14일 / 21일 event별 건수 (bhvr + dst 합산)."""
    today = date.today()

    def query_table(table):
        return database.run_query(
            f"SELECT {EVENT_COL} AS et, "
            f"  COUNT(*) FILTER (WHERE DATE(reg_dt) = %s::date)                      AS today, "
            f"  COUNT(*) FILTER (WHERE DATE(reg_dt) = %s::date - INTERVAL '7 days')  AS d7, "
            f"  COUNT(*) FILTER (WHERE DATE(reg_dt) = %s::date - INTERVAL '14 days') AS d14, "
            f"  COUNT(*) FILTER (WHERE DATE(reg_dt) = %s::date - INTERVAL '21 days') AS d21 "
            f"FROM {table} "
            f"WHERE DATE(reg_dt) IN (%s::date, %s::date - INTERVAL '7 days', "
            f"                       %s::date - INTERVAL '14 days', %s::date - INTERVAL '21 days') "
            f"GROUP BY {EVENT_COL}",
            [today, today, today, today, today, today, today, today],
        )

    agg = {}
    for r in query_table(BHVR_TABLE) + query_table(DST_TABLE):
        et = r["et"]
        if et not in agg:
            agg[et] = {"today": 0, "d7": 0, "d14": 0, "d21": 0}
        agg[et]["today"] += r["today"] or 0
        agg[et]["d7"]    += r["d7"]    or 0
        agg[et]["d14"]   += r["d14"]   or 0
        agg[et]["d21"]   += r["d21"]   or 0

    events = [{
        "event": e,
        "today": agg.get(e, {}).get("today", 0),
        "d7":    agg.get(e, {}).get("d7",    0),
        "d14":   agg.get(e, {}).get("d14",   0),
        "d21":   agg.get(e, {}).get("d21",   0),
    } for e in ALL_EVENTS]

    return {
        "date":   str(today),
        "as_of":  datetime.now().strftime("%H:%M"),
        "events": events,
    }


@router.get("/summary")
def get_summary():
    """bhvr / dst 각각 오늘·7일·30일 요약 + 30일 일별 line + 30일 일별 상세."""
    today  = date.today()
    now    = datetime.now()
    start30 = today - timedelta(days=29)

    def table_data(table, events_list):
        # 요약 counts
        s = database.run_query(
            f"SELECT "
            f"  COUNT(*) FILTER (WHERE reg_dt >= %s::date)                      AS today, "
            f"  COUNT(*) FILTER (WHERE reg_dt >= %s::date - INTERVAL '7 days')  AS d7, "
            f"  COUNT(*) FILTER (WHERE reg_dt >= %s::date - INTERVAL '30 days') AS d30 "
            f"FROM {table} WHERE reg_dt >= %s::date - INTERVAL '30 days'",
            [today, today, today, today],
        )
        r = s[0] if s else {}
        summary = {
            "today":    int(r.get("today", 0) or 0),
            "last_7d":  int(r.get("d7",    0) or 0),
            "last_30d": int(r.get("d30",   0) or 0),
        }

        # 일별 합계 (line chart용)
        daily_rows = database.run_query(
            f"SELECT DATE(reg_dt) AS day, COUNT(*) AS cnt "
            f"FROM {table} "
            f"WHERE reg_dt >= %s::date - INTERVAL '30 days' "
            f"GROUP BY DATE(reg_dt) ORDER BY day",
            [today],
        )
        daily_map = {str(r["day"]): int(r["cnt"]) for r in daily_rows}

        line = []
        for i in range(30):
            d  = start30 + timedelta(days=i)
            ds = str(d)
            line.append({"date": ds, "label": KR_DAYS[d.weekday()], "total": daily_map.get(ds, 0)})

        # 일별 event 상세
        detail_rows = database.run_query(
            f"SELECT DATE(reg_dt) AS day, {EVENT_COL} AS et, COUNT(*) AS cnt "
            f"FROM {table} "
            f"WHERE reg_dt >= %s::date - INTERVAL '30 days' "
            f"GROUP BY DATE(reg_dt), {EVENT_COL} ORDER BY day",
            [today],
        )
        detail_map = {}
        for r in detail_rows:
            ds = str(r["day"])
            if ds not in detail_map:
                detail_map[ds] = {}
            detail_map[ds][r["et"]] = int(r["cnt"])

        detail = []
        for i in range(30):
            d  = start30 + timedelta(days=i)
            ds = str(d)
            row = {"date": ds, "label": KR_DAYS[d.weekday()]}
            day_ev = detail_map.get(ds, {})
            total  = 0
            for ev in events_list:
                cnt = day_ev.get(ev, 0)
                row[ev] = cnt
                total  += cnt
            row["total"] = total
            detail.append(row)

        return {"summary": summary, "line": line, "detail": detail}

    return {
        "as_of": now.strftime("%H:%M"),
        "date":  str(today),
        "bhvr":  table_data(BHVR_TABLE, BHVR_EVENTS),
        "dst":   table_data(DST_TABLE,  DST_EVENTS),
    }


@router.get("/histogram")
def get_histogram():
    """최근 14일 bhvr 테이블 일별·event별 건수."""
    today = date.today()
    start = today - timedelta(days=13)

    rows = database.run_query(
        f"SELECT DATE(reg_dt) AS day, {EVENT_COL} AS et, COUNT(*) AS cnt "
        f"FROM {BHVR_TABLE} "
        f"WHERE reg_dt >= %s "
        f"GROUP BY DATE(reg_dt), {EVENT_COL} "
        f"ORDER BY day",
        [start],
    )

    day_map = {}
    for r in rows:
        k = str(r["day"])
        if k not in day_map:
            day_map[k] = {}
        day_map[k][r["et"]] = r["cnt"]

    days = []
    for i in range(14):
        d  = start + timedelta(days=i)
        ds = str(d)
        days.append({"date": ds, "label": KR_DAYS[d.weekday()], "events": day_map.get(ds, {})})

    return {"days": days}


# ── /api/stats/period_query ────────────────────────────────────────────────────

@router.get("/period_query")
def get_period_query(
    ref_date:  str = Query(default=None),
    time_from: str = Query(default="00:00"),
    time_to:   str = Query(default="23:59"),
    event:     str = Query(default="전체"),
):
    """기간별 조회: 특정 시간대의 일별 이벤트 건수 (30일 list, 14일 chart용)."""
    today = date.today()
    try:
        ref = date.fromisoformat(ref_date) if ref_date else today
    except ValueError:
        ref = today
    start30 = ref - timedelta(days=29)

    time_cond = "AND reg_dt::time BETWEEN %s::time AND %s::time"

    def query_table(table, ev_cond, ev_params):
        return database.run_query(
            f"SELECT DATE(reg_dt) AS day, COUNT(*) AS cnt "
            f"FROM {table} "
            f"WHERE DATE(reg_dt) BETWEEN %s AND %s "
            f"{time_cond} {ev_cond} "
            f"GROUP BY DATE(reg_dt) ORDER BY day",
            [start30, ref, time_from, time_to] + ev_params,
        )

    if event == "전체":
        rows  = query_table(BHVR_TABLE, "", [])
        rows += query_table(DST_TABLE,  "", [])
    elif event in BHVR_EVENTS:
        rows = query_table(BHVR_TABLE, f"AND {EVENT_COL} = %s", [event])
    elif event in DST_EVENTS:
        rows = query_table(DST_TABLE,  f"AND {EVENT_COL} = %s", [event])
    else:
        rows  = query_table(BHVR_TABLE, "", [])
        rows += query_table(DST_TABLE,  "", [])

    day_map = {}
    for r in rows:
        ds = str(r["day"])
        day_map[ds] = day_map.get(ds, 0) + int(r["cnt"] or 0)

    days = []
    for i in range(30):
        d  = start30 + timedelta(days=i)
        ds = str(d)
        days.append({
            "date":  ds,
            "label": KR_DAYS[d.weekday()],
            "count": day_map.get(ds, 0),
        })

    return {
        "ref_date":  str(ref),
        "time_from": time_from,
        "time_to":   time_to,
        "event":     event,
        "days":      days,
    }
