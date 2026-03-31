import matplotlib.pyplot as plt
import requests
import gradio as gr
from config import ALL_EVENTS, BHVR_EVENTS, DST_EVENTS, API_BASE_URL
from ui_charts import (build_histogram, build_line_chart, build_server_line,
    build_server_histogram, build_processing_bar, build_processing_trend,
    build_processing_count_trend, build_precision_bar, build_precision_trend,
    build_precision_count_trend, build_false_cause_event_chart, build_time_heatmap,
    build_time_slot_bar, build_time_line, build_period_chart)
from ui_render import (render_today_events, render_summary_counts, render_detail_table,
    render_nodes_table, render_server_stats, render_processing_cards,
    render_processing_event_table, render_processing_node_table, render_precision_cards,
    render_precision_event_table, render_precision_node_table, render_stats, render_list,
    render_node_stats, render_false_cause_completion, render_false_cause_event_table,
    render_false_cause_user_table, render_time_dist_cards, render_period_list)


def api_get(path: str, params: dict = None) -> dict:
    try:
        r = requests.get(f"{API_BASE_URL}{path}", params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def load_today_tab():
    today_html = render_today_events(api_get("/api/stats/today"))
    histogram  = build_histogram(api_get("/api/stats/histogram"))
    return today_html, histogram


def load_summary_tab():
    data      = api_get("/api/stats/summary")
    empty_fig = plt.figure(figsize=(20, 4))

    if "error" in data:
        err = f"<p style='color:red'>⚠ {data['error']}</p>"
        return err, empty_fig, err, err, empty_fig, err

    bhvr = data.get("bhvr", {})
    dst  = data.get("dst",  {})

    return (
        render_summary_counts(bhvr.get("summary", {}), "🚶 행동 분석 (bhvr) 요약"),
        build_line_chart(bhvr.get("line", []), "행동 분석 일별 추이 (30일)"),
        render_detail_table(bhvr.get("detail", []), BHVR_EVENTS),
        render_summary_counts(dst.get("summary",  {}), "🌊 재난 분석 (dst) 요약"),
        build_line_chart(dst.get("line",  []), "재난 분석 일별 추이 (30일)"),
        render_detail_table(dst.get("detail",  []), DST_EVENTS),
    )


def get_viewer_names() -> list:
    data = api_get("/api/server/nodes")
    nodes = data.get("nodes", [])
    return sorted(set(n["viewer_name"] for n in nodes if n.get("viewer_name")))


def do_load_nodes_by_viewer(viewer_name: str) -> str:
    data  = api_get("/api/server/nodes")
    nodes = data.get("nodes", [])
    if viewer_name:
        nodes = [n for n in nodes if n.get("viewer_name") == viewer_name]
    return render_nodes_table(nodes)


def do_import_excel(file_obj):
    if file_obj is None:
        return "<p style='color:orange'>파일을 선택하세요</p>", gr.update(), ""
    file_path = file_obj.name if hasattr(file_obj, "name") else file_obj
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{API_BASE_URL}/api/server/import",
                files={"file": ("upload.xlsx", f,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                timeout=30,
            )
        if r.ok:
            n       = r.json().get("imported", 0)
            viewers = get_viewer_names()
            first   = viewers[0] if viewers else None
            nodes_html = do_load_nodes_by_viewer(first) if first else ""
            return (
                f"<p style='color:green'>✓ {n}건 임포트 완료 &nbsp;·&nbsp; 뷰어 {len(viewers)}개</p>",
                gr.update(choices=viewers, value=first),
                nodes_html,
            )
        return f"<p style='color:red'>⚠ {r.text}</p>", gr.update(), ""
    except Exception as e:
        return f"<p style='color:red'>⚠ {e}</p>", gr.update(), ""


def do_add_node(viewer, node_id, mgmt, name):
    if not viewer.strip() or not node_id.strip():
        return "<p style='color:orange'>Viewer Name과 Node ID는 필수입니다</p>", do_load_nodes_by_viewer(viewer)
    try:
        r = requests.post(
            f"{API_BASE_URL}/api/server/nodes",
            json={"viewer_name": viewer, "node_id": node_id,
                  "management_code": mgmt, "name": name},
            timeout=10,
        )
        if r.ok:
            return "<p style='color:green'>✓ 추가 완료</p>", do_load_nodes_by_viewer(viewer)
        return f"<p style='color:red'>⚠ {r.text}</p>", do_load_nodes_by_viewer(viewer)
    except Exception as e:
        return f"<p style='color:red'>⚠ {e}</p>", do_load_nodes_by_viewer(viewer)


def do_load_server_stats():
    data = api_get("/api/server/stats")
    return render_server_stats(data), build_server_line(data), build_server_histogram(data)


def do_load_processing(period: str):
    try:
        data      = api_get("/api/analysis/processing", {"period": period})
        empty_fig = plt.figure(figsize=(20, 4))
        if "error" in data:
            err = f"<p style='color:red'>⚠ {data['error']}</p>"
            return err, empty_fig, err, err, empty_fig, empty_fig
        daily = data.get("daily", [])
        return (
            render_processing_cards(data.get("summary", {})),
            build_processing_bar(data.get("events", [])),
            render_processing_event_table(data.get("events", [])),
            render_processing_node_table(data.get("nodes", [])),
            build_processing_trend(daily),
            build_processing_count_trend(daily),
        )
    except Exception as e:
        import traceback
        err = f"<p style='color:red'>⚠ Python hatası: <pre>{traceback.format_exc()}</pre></p>"
        empty_fig = plt.figure(figsize=(20, 4))
        return err, empty_fig, err, err, empty_fig, empty_fig


def do_load_precision(period: str):
    data      = api_get("/api/analysis/precision", {"period": period})
    empty_fig = plt.figure(figsize=(20, 4))
    if "error" in data:
        err = f"<p style='color:red'>⚠ {data['error']}</p>"
        return err, empty_fig, err, err, empty_fig, empty_fig
    daily = data.get("daily", [])
    return (
        render_precision_cards(data.get("summary", {})),
        build_precision_bar(data.get("events", [])),
        render_precision_event_table(data.get("events", [])),
        render_precision_node_table(data.get("nodes", [])),
        build_precision_trend(daily),
        build_precision_count_trend(daily),
    )


def do_search(start_dt: str, end_dt: str, selected_events: list, node_id_input: str):
    if not selected_events:
        msg = "<p style='color:orange'>⚠ 이벤트를 하나 이상 선택하세요</p>"
        return msg, msg, msg

    node_ids = [n.strip() for n in node_id_input.split(",") if n.strip()] if node_id_input else []

    params = {"start_dt": start_dt, "end_dt": end_dt, "events": selected_events}
    if node_ids:
        params["node_id"] = node_ids

    stats_html = render_stats(api_get("/api/search/stats", params))
    list_html  = render_list(api_get("/api/search/list",   params))
    node_html  = render_node_stats(
        api_get("/api/search/node-stats", params),
        start_dt, end_dt, selected_events,
    )
    return stats_html, list_html, node_html


def do_load_false_cause(period: str):
    try:
        data      = api_get("/api/analysis/false_cause", {"period": period})
        empty_fig = plt.figure(figsize=(10, 6))
        if "error" in data:
            err = f"<p style='color:red'>⚠ {data['error']}</p>"
            return err, empty_fig, err, err
        all_causes = data.get("all_causes", [])
        return (
            render_false_cause_completion(data.get("completion", {})),
            build_false_cause_event_chart(data.get("events", []), all_causes),
            render_false_cause_event_table(data.get("events", []), all_causes),
            render_false_cause_user_table(data.get("users",  []), all_causes),
        )
    except Exception as e:
        import traceback
        err = f"<p style='color:red'>⚠ <pre>{traceback.format_exc()}</pre></p>"
        return err, plt.figure(figsize=(10, 6)), err, err


def do_load_time_dist_all(period: str):
    try:
        data      = api_get("/api/analysis/time_dist_all", {"period": period})
        empty_fig = plt.figure(figsize=(20, 4))
        if "error" in data:
            err = f"<p style='color:red'>⚠ {data['error']}</p>"
            return err, empty_fig, empty_fig, empty_fig
        return (
            render_time_dist_cards(data.get("cards", {}), total_label="이벤트 총계"),
            build_time_heatmap(data.get("hourly_events", {}), title="시간대 × 이벤트 히트맵 (전체)"),
            build_time_line(data.get("hour_total", []), title="시간별 이벤트 분포 (0~23시)"),
            build_time_slot_bar(data.get("slots", [])),
        )
    except Exception as e:
        import traceback
        err = f"<p style='color:red'>⚠ <pre>{traceback.format_exc()}</pre></p>"
        return err, plt.figure(figsize=(20, 4)), plt.figure(figsize=(20, 4)), plt.figure(figsize=(20, 4))


def do_load_time_dist(period: str):
    try:
        data      = api_get("/api/analysis/time_dist", {"period": period})
        empty_fig = plt.figure(figsize=(20, 4))
        if "error" in data:
            err = f"<p style='color:red'>⚠ {data['error']}</p>"
            return err, empty_fig, empty_fig, empty_fig
        return (
            render_time_dist_cards(data.get("cards", {})),
            build_time_heatmap(data.get("hourly_events", {})),
            build_time_line(data.get("hour_total", [])),
            build_time_slot_bar(data.get("slots", [])),
        )
    except Exception as e:
        import traceback
        err = f"<p style='color:red'>⚠ <pre>{traceback.format_exc()}</pre></p>"
        return err, plt.figure(figsize=(20, 4)), plt.figure(figsize=(20, 4)), plt.figure(figsize=(20, 4))


def do_period_query(ref_date: str, time_from: str, time_to: str, event: str):
    params = {
        "ref_date":  (ref_date or "").strip(),
        "time_from": (time_from or "00:00").strip(),
        "time_to":   (time_to   or "23:59").strip(),
        "event":     event or "전체",
    }
    data      = api_get("/api/stats/period_query", params)
    empty_fig = plt.figure(figsize=(14, 5))
    if "error" in data:
        err = f"<p style='color:red'>⚠ {data['error']}</p>"
        return empty_fig, err
    return build_period_chart(data), render_period_list(data)
