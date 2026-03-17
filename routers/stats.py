from fastapi import APIRouter
from datetime import date, datetime, timedelta

import database
from config import BHVR_TABLE, DST_TABLE, EVENT_COL, ALL_EVENTS

router = APIRouter(prefix="/api/stats", tags=["stats"])

KR_DAYS = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}


@router.get("/today")
def get_today():
    """오늘 00:00 ~ 현재 시각까지 event 별 건수 (bhvr + dst 합산)."""
    today = date.today()
    rows = database.run_query(
        f"SELECT {EVENT_COL} AS et, COUNT(*) AS cnt FROM {BHVR_TABLE} "
        f"WHERE reg_dt >= %s GROUP BY {EVENT_COL} "
        f"UNION ALL "
        f"SELECT {EVENT_COL} AS et, COUNT(*) AS cnt FROM {DST_TABLE} "
        f"WHERE reg_dt >= %s GROUP BY {EVENT_COL}",
        [today, today],
    )
    agg = {}
    for r in rows:
        agg[r["et"]] = agg.get(r["et"], 0) + r["cnt"]

    # ALL_EVENTS 순서로 정렬, 0건도 포함
    events = [{"event": e, "count": agg.get(e, 0)} for e in ALL_EVENTS]

    return {
        "date":  str(today),
        "as_of": datetime.now().strftime("%H:%M"),
        "events": events,
    }


@router.get("/summary")
def get_summary():
    """bhvr / dst 테이블 각각 오늘 · 7일 · 30일 총 건수."""
    today = date.today()
    now   = datetime.now()

    def table_counts(table):
        rows = database.run_query(
            f"SELECT "
            f"  COUNT(*) FILTER (WHERE reg_dt >= %s::date)                        AS today, "
            f"  COUNT(*) FILTER (WHERE reg_dt >= %s::date - INTERVAL '7 days')    AS d7, "
            f"  COUNT(*) FILTER (WHERE reg_dt >= %s::date - INTERVAL '30 days')   AS d30 "
            f"FROM {table} WHERE reg_dt >= %s::date - INTERVAL '30 days'",
            [today, today, today, today],
        )
        r = rows[0] if rows else {}
        return {
            "today":    int(r.get("today", 0)),
            "last_7d":  int(r.get("d7",    0)),
            "last_30d": int(r.get("d30",   0)),
        }

    return {
        "as_of": now.strftime("%H:%M"),
        "date":  str(today),
        "bhvr":  table_counts(BHVR_TABLE),
        "dst":   table_counts(DST_TABLE),
    }


@router.get("/histogram")
def get_histogram():
    """최근 14일 bhvr 테이블 일별 · event별 건수 (히스토그램용)."""
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

    # 날짜별 딕셔너리로 정리
    day_map = {}
    for r in rows:
        k = str(r["day"])
        if k not in day_map:
            day_map[k] = {}
        day_map[k][r["et"]] = r["cnt"]

    days = []
    for i in range(14):
        d = start + timedelta(days=i)
        ds = str(d)
        days.append({
            "date":   ds,
            "label":  KR_DAYS[d.weekday()],
            "events": day_map.get(ds, {}),
        })

    return {"days": days}
