import json
import html as htmllib
import gradio as gr
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from config import ALL_EVENTS, BHVR_EVENTS, DST_EVENTS, API_BASE_URL

sns.set_theme(style="whitegrid")
plt.rcParams["font.family"]       = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# ── API helper ────────────────────────────────────────────────────────────────

def api_get(path: str, params: dict = None) -> dict:
    try:
        r = requests.get(f"{API_BASE_URL}{path}", params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Stil sabitleri ────────────────────────────────────────────────────────────

TH   = "style='border:1px solid rgba(128,128,128,0.4);padding:8px;background:rgba(128,128,128,0.15);text-align:left;font-weight:600'"
TH_C = "style='border:1px solid rgba(128,128,128,0.4);padding:8px;background:rgba(128,128,128,0.15);text-align:center;font-weight:600'"
TD   = "style='border:1px solid rgba(128,128,128,0.3);padding:8px'"
TD_C = "style='border:1px solid rgba(128,128,128,0.3);padding:8px;text-align:center'"


# ── 오늘의 통계 렌더러 ─────────────────────────────────────────────────────────

def render_today_events(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    events = data.get("events", [])
    if not events:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    d     = data.get("date", "")
    as_of = data.get("as_of", "")
    html  = f"<p style='opacity:0.6;margin:0 0 8px'>📅 {d} &nbsp;·&nbsp; {as_of} 기준</p>"
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%'>"
    html += (
        f"<tr>"
        f"<th {TH}>이벤트</th>"
        f"<th {TH_C}>오늘</th>"
        f"<th {TH_C}>7일전</th>"
        f"<th {TH_C}>14일전</th>"
        f"<th {TH_C}>21일전</th>"
        f"</tr>"
    )
    for row in events:
        html += (
            f"<tr>"
            f"<td {TD}>{row['event']}</td>"
            f"<td {TD_C}><b>{row['today']}</b></td>"
            f"<td {TD_C}>{row['d7']}</td>"
            f"<td {TD_C}>{row['d14']}</td>"
            f"<td {TD_C}>{row['d21']}</td>"
            f"</tr>"
        )
    html += "</table></div>"
    return html


def build_histogram(data: dict):
    fig, ax = plt.subplots(figsize=(20, 10))
    if "error" in data or not data.get("days"):
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    days   = data["days"]
    labels = [f"{d['date'][5:]}({d['label']})" for d in days]

    all_ev = []
    seen   = set()
    for d in days:
        for k in d.get("events", {}):
            if k not in seen:
                all_ev.append(k)
                seen.add(k)

    colors = [
        "#4C78A8", "#F58518", "#E45756", "#72B7B2",
        "#54A24B", "#EECA3B", "#B279A2", "#FF9DA6",
        "#9D755D", "#BAB0AC",
    ]

    bottoms = [0] * len(days)
    for i, ev in enumerate(all_ev):
        counts = [d.get("events", {}).get(ev, 0) for d in days]
        ax.bar(labels, counts, bottom=bottoms,
               label=ev, color=colors[i % len(colors)], width=0.6)
        bottoms = [b + c for b, c in zip(bottoms, counts)]

    ax.tick_params(axis="x", rotation=45, labelsize=16)
    ax.tick_params(axis="y", labelsize=15)
    ax.legend(loc="upper right", bbox_to_anchor=(1, 1.12),
              ncol=len(all_ev), fontsize=15, framealpha=0.6,
              markerscale=1.8, handlelength=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def load_today_tab():
    today_html = render_today_events(api_get("/api/stats/today"))
    histogram  = build_histogram(api_get("/api/stats/histogram"))
    return today_html, histogram


# ── 요약 렌더러 ───────────────────────────────────────────────────────────────

def render_summary_counts(summary: dict, title: str) -> str:
    html  = f"<h4 style='margin:0 0 8px'>{title}</h4>"
    html += "<table style='border-collapse:collapse;width:300px'>"
    html += f"<tr><th {TH}>기간</th><th {TH}>건수</th></tr>"
    html += f"<tr><td {TD}>오늘</td><td {TD_C}><b>{summary.get('today', 0)}</b></td></tr>"
    html += f"<tr><td {TD}>최근 7일</td><td {TD_C}><b>{summary.get('last_7d', 0)}</b></td></tr>"
    html += f"<tr><td {TD}>최근 30일</td><td {TD_C}><b>{summary.get('last_30d', 0)}</b></td></tr>"
    html += "</table>"
    return html


def build_line_chart(line_data: list, title: str):
    fig, ax = plt.subplots(figsize=(20, 4))
    if not line_data:
        return fig

    labels = [f"{d['date'][5:]}({d['label']})" for d in line_data]
    totals = [d["total"] for d in line_data]
    xs     = range(len(labels))

    ax.plot(xs, totals, marker="o", linewidth=2.5, markersize=6, color="#4C78A8")
    ax.fill_between(xs, totals, alpha=0.12, color="#4C78A8")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=45, fontsize=12)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_title(title, fontsize=14, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def render_detail_table(detail: list, events_list: list) -> str:
    if not detail:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto;max-height:420px;overflow-y:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += "<tr>"
    html += f"<th {TH}>날짜</th>"
    html += f"<th {TH_C}>합계</th>"
    for ev in events_list:
        html += f"<th {TH_C}>{ev}</th>"
    html += "</tr>"

    for row in detail:
        faded = " style='opacity:0.35'" if row.get("total", 0) == 0 else ""
        html += f"<tr{faded}>"
        html += f"<td {TD}>{row['date'][5:]}({row['label']})</td>"
        t = row.get("total", 0)
        html += f"<td {TD_C}><b>{t if t else ''}</b></td>"
        for ev in events_list:
            v = row.get(ev, 0)
            html += f"<td {TD_C}>{v if v else ''}</td>"
        html += "</tr>"

    html += "</table></div>"
    return html


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


# ── 서버 통계 렌더러 ──────────────────────────────────────────────────────────

def render_nodes_table(nodes: list) -> str:
    if not nodes:
        return "<p style='opacity:0.5'>등록된 노드 없음</p>"

    api_json = json.dumps(API_BASE_URL)
    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr>"
        f"<th {TH}>ID</th><th {TH}>Viewer Name</th><th {TH}>Node ID</th>"
        f"<th {TH}>Management Code</th><th {TH}>Name</th><th {TH}>삭제</th>"
        f"</tr>"
    )
    for r in nodes:
        row_id  = r["id"]
        onclick = htmllib.escape(
            f"(async function(btn){{"
            f"var res=await fetch({api_json}+'/api/server/nodes/{row_id}',{{method:'DELETE'}});"
            f"if(res.ok)btn.closest('tr').remove();"
            f"else alert('삭제 실패');"
            f"}})(this)"
        )
        html += (
            f"<tr>"
            f"<td {TD_C}>{row_id}</td>"
            f"<td {TD}>{r['viewer_name']}</td>"
            f"<td {TD}>{r['node_id']}</td>"
            f"<td {TD}>{r.get('management_code', '')}</td>"
            f"<td {TD}>{r.get('name', '')}</td>"
            f"<td {TD_C}>"
            f"<button onclick=\"{onclick}\" style='padding:3px 10px;cursor:pointer;"
            f"border-radius:4px;border:1px solid rgba(220,80,80,0.5);"
            f"background:rgba(220,80,80,0.08);font-size:12px'>삭제</button>"
            f"</td></tr>"
        )
    html += "</table></div>"
    return html


def render_server_stats(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    viewers = data.get("viewers", [])
    events  = data.get("events",  ALL_EVENTS)
    if not viewers:
        return "<p style='opacity:0.5'>데이터 없음 (노드 등록 필요)</p>"

    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += "<tr>"
    html += f"<th {TH}>Viewer Name</th>"
    html += f"<th {TH_C}>합계</th>"
    for ev in events:
        html += f"<th {TH_C}>{ev}</th>"
    html += "</tr>"

    for v in viewers:
        html += "<tr>"
        html += f"<td {TD}><b>{v['viewer_name']}</b></td>"
        html += f"<td {TD_C}><b>{v['total']}</b></td>"
        for ev in events:
            html += f"<td {TD_C}>{v['events'].get(ev, 0)}</td>"
        html += "</tr>"

    html += "</table></div>"
    return html


def build_server_line(data: dict):
    """Tüm viewerları tek grafikte karşılaştıran line chart."""
    viewers = data.get("viewers", []) if isinstance(data, dict) else []
    if not viewers:
        fig, ax = plt.subplots(figsize=(20, 4))
        ax.axis("off")
        return fig

    colors = ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B", "#EECA3B"]
    fig, ax = plt.subplots(figsize=(20, 4))
    all_dates = None

    for i, v in enumerate(viewers):
        daily  = v.get("daily", [])
        dates  = [d["date"][5:] for d in daily]
        totals = [sum(d.get(e, 0) for e in ALL_EVENTS) for d in daily]
        if all_dates is None:
            all_dates = dates
        ax.plot(range(len(dates)), totals, marker="o", linewidth=2.5, markersize=6,
                color=colors[i % len(colors)], label=v["viewer_name"])

    if all_dates:
        ax.set_xticks(range(len(all_dates)))
        ax.set_xticklabels(all_dates, rotation=45, fontsize=13)
    ax.tick_params(axis="y", labelsize=12)
    ax.legend(fontsize=13)
    ax.set_title("일별 총 이벤트 (최근 14일)", fontsize=15, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def build_server_histogram(data: dict):
    viewers = data.get("viewers", []) if isinstance(data, dict) else []
    events  = data.get("events",  ALL_EVENTS)

    if not viewers:
        fig, ax = plt.subplots(figsize=(20, 4))
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    n   = len(viewers)
    fig, axes = plt.subplots(n, 1, figsize=(20, 5 * n), squeeze=False)

    colors = [
        "#4C78A8", "#F58518", "#E45756", "#72B7B2",
        "#54A24B", "#EECA3B", "#B279A2", "#FF9DA6",
        "#9D755D", "#BAB0AC",
    ]

    for i, v in enumerate(viewers):
        ax     = axes[i][0]
        daily  = v.get("daily", [])
        labels = [d["date"][5:] for d in daily]

        bottoms = [0] * len(daily)
        drawn   = []
        for j, ev in enumerate(events):
            counts = [d.get(ev, 0) for d in daily]
            if any(c > 0 for c in counts):
                ax.bar(labels, counts, bottom=bottoms,
                       label=ev, color=colors[j % len(colors)], width=0.6)
                drawn.append(ev)
            bottoms = [b + c for b, c in zip(bottoms, counts)]

        ax.set_title(f"🖥  {v['viewer_name']}  (총 {v['total']}건)", fontsize=15, pad=10)
        ax.tick_params(axis="x", rotation=45, labelsize=13)
        ax.tick_params(axis="y", labelsize=12)
        if drawn:
            ax.legend(loc="upper right", bbox_to_anchor=(1, 1.12),
                      ncol=len(drawn), fontsize=12, framealpha=0.6,
                      markerscale=1.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.tight_layout(h_pad=3)
    return fig


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


# ── 분석 렌더러 ───────────────────────────────────────────────────────────────

# ── 처리 현황 ─────────────────────────────────────────────────────────────────

def render_processing_cards(summary: dict) -> str:
    if not summary:
        return ""
    tot  = summary.get("total", 0)
    proc = summary.get("processed", 0)
    unpr = summary.get("unprocessed", 0)
    rate = summary.get("rate", 0.0)

    cs = "border-radius:10px;padding:18px 24px;text-align:center;flex:1;min-width:120px"
    return (
        "<div style='display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px'>"
        f"<div style='{cs};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2)'>"
        f"<div style='font-size:2rem;font-weight:700'>{tot:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>전체</div></div>"

        f"<div style='{cs};background:rgba(84,162,75,0.08);border:1px solid rgba(84,162,75,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#54A24B'>{proc:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>확인 완료</div></div>"

        f"<div style='{cs};background:rgba(228,87,86,0.08);border:1px solid rgba(228,87,86,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#E45756'>{unpr:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>미확인</div></div>"

        f"<div style='{cs};background:rgba(76,120,168,0.08);border:1px solid rgba(76,120,168,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#4C78A8'>{rate}%</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>처리율</div></div>"
        "</div>"
    )


def build_processing_bar(events: list):
    fig, ax = plt.subplots(figsize=(14, 5))
    active = [e for e in events if e["total"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels = [e["event"]       for e in active]
    proc_v = [e["processed"]   for e in active]
    unpr_v = [e["unprocessed"] for e in active]
    x, w   = range(len(labels)), 0.35

    b1 = ax.bar([i - w/2 for i in x], proc_v, w, label="확인 완료", color="#54A24B", alpha=0.85)
    b2 = ax.bar([i + w/2 for i in x], unpr_v, w, label="미확인",    color="#E45756", alpha=0.85)

    for bar in b1 + b2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, str(int(h)),
                    ha="center", va="bottom", fontsize=10)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=13)
    ax.tick_params(axis="y", labelsize=12)
    ax.legend(fontsize=13)
    ax.set_title("이벤트별 처리 현황", fontsize=14, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def render_processing_event_table(events: list) -> str:
    active = [e for e in events if e["total"] > 0]
    if not active:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH}>이벤트</th>"
        f"<th {TH_C}>확인 완료</th><th {TH_C}>미확인</th>"
        f"<th {TH_C}>합계</th><th {TH_C}>미확인율 %</th></tr>"
    )
    for e in active:
        rate = e["unpr_rate"]
        rc   = "#E45756" if rate > 30 else "#F58518" if rate > 10 else "inherit"
        html += (
            f"<tr><td {TD}><b>{e['event']}</b></td>"
            f"<td {TD_C} style='color:#54A24B'>{e['processed']:,}</td>"
            f"<td {TD_C} style='color:#E45756'>{e['unprocessed']:,}</td>"
            f"<td {TD_C}>{e['total']:,}</td>"
            f"<td {TD_C}><b style='color:{rc}'>{rate}%</b></td></tr>"
        )
    html += "</table></div>"
    return html


def render_processing_node_table(nodes: list) -> str:
    if not nodes:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto;max-height:400px;overflow-y:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH}>Node ID</th><th {TH}>Name</th><th {TH_C}>Ch</th>"
        f"<th {TH_C}>확인 완료</th><th {TH_C}>미확인</th>"
        f"<th {TH_C}>합계</th><th {TH_C}>미확인율 %</th></tr>"
    )
    for n in nodes:
        rate = n["unpr_rate"]
        rc   = "#E45756" if rate > 30 else "#F58518" if rate > 10 else "inherit"
        html += (
            f"<tr><td {TD}>{n['node_id']}</td>"
            f"<td {TD}>{n.get('node_name', '')}</td>"
            f"<td {TD_C}>{n['ch']}</td>"
            f"<td {TD_C} style='color:#54A24B'>{n['processed']:,}</td>"
            f"<td {TD_C} style='color:#E45756'>{n['unprocessed']:,}</td>"
            f"<td {TD_C}>{n['total']:,}</td>"
            f"<td {TD_C}><b style='color:{rc}'>{rate}%</b></td></tr>"
        )
    html += "</table></div>"
    return html


def build_processing_trend(daily: list):
    """미확인율 % line chart + 평균 점선."""
    fig, ax = plt.subplots(figsize=(20, 4))
    active = [d for d in daily if d["total"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels    = [f"{d['date'][5:]}({d['label']})" for d in daily]
    rates     = [d["unpr_rate"] for d in daily]
    xs        = range(len(labels))
    total_unp = sum(d["unprocessed"] for d in daily)
    total_all = sum(d["total"]       for d in daily)
    avg       = round(total_unp / total_all * 100, 1) if total_all > 0 else 0

    ax.plot(xs, rates, marker="o", linewidth=2.5, markersize=6,
            color="#E45756", label="미확인율 %")
    ax.fill_between(xs, rates, alpha=0.10, color="#E45756")
    ax.axhline(y=avg, color="#F58518", linewidth=1.5, linestyle="--",
               label=f"평균 {avg:.1f}%")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=45, fontsize=11)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylabel("미확인율 %", fontsize=12)
    ax.set_title("일별 미확인율 추이", fontsize=14, pad=12)
    ax.legend(fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def build_processing_count_trend(daily: list):
    """확인 완료 vs 미확인 건수 두 선."""
    fig, ax = plt.subplots(figsize=(20, 4))
    active = [d for d in daily if d["total"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels = [f"{d['date'][5:]}({d['label']})" for d in daily]
    proc_v = [d["processed"]   for d in daily]
    unpr_v = [d["unprocessed"] for d in daily]
    xs     = range(len(labels))

    ax.plot(xs, proc_v, marker="o", linewidth=2.5, markersize=6,
            color="#54A24B", label="확인 완료")
    ax.plot(xs, unpr_v, marker="o", linewidth=2.5, markersize=6,
            color="#E45756", label="미확인")
    ax.fill_between(xs, proc_v, alpha=0.08, color="#54A24B")
    ax.fill_between(xs, unpr_v, alpha=0.08, color="#E45756")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=45, fontsize=11)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylabel("건수", fontsize=12)
    ax.set_title("일별 확인 완료 / 미확인 건수", fontsize=14, pad=12)
    ax.legend(fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


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


# ── 정탐 / 오탐 ───────────────────────────────────────────────────────────────

def render_precision_cards(summary: dict) -> str:
    if not summary:
        return ""
    total = summary.get("total", 0)
    jd    = summary.get("jeongdam", 0)
    od    = summary.get("odam", 0)
    prec  = summary.get("precision", 0.0)

    cs = "border-radius:10px;padding:18px 24px;text-align:center;flex:1;min-width:120px"
    return (
        "<div style='display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px'>"
        f"<div style='{cs};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2)'>"
        f"<div style='font-size:2rem;font-weight:700'>{total:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>검토 완료</div></div>"

        f"<div style='{cs};background:rgba(76,120,168,0.08);border:1px solid rgba(76,120,168,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#4C78A8'>{jd:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>정탐</div></div>"

        f"<div style='{cs};background:rgba(228,87,86,0.08);border:1px solid rgba(228,87,86,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#E45756'>{od:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>오탐</div></div>"

        f"<div style='{cs};background:rgba(84,162,75,0.08);border:1px solid rgba(84,162,75,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#54A24B'>{prec}%</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>Precision</div></div>"
        "</div>"
    )


def build_precision_bar(events: list):
    """Event bazlı 정탐 vs 오탐 grouped bar chart."""
    fig, ax = plt.subplots(figsize=(14, 5))
    active = [e for e in events if e["total"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels  = [e["event"]    for e in active]
    jd_vals = [e["jeongdam"] for e in active]
    od_vals = [e["odam"]     for e in active]
    x, w    = range(len(labels)), 0.35

    b1 = ax.bar([i - w/2 for i in x], jd_vals, w, label="정탐", color="#4C78A8", alpha=0.85)
    b2 = ax.bar([i + w/2 for i in x], od_vals, w, label="오탐", color="#E45756", alpha=0.85)

    for bar in b1 + b2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, str(int(h)),
                    ha="center", va="bottom", fontsize=10)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=13)
    ax.tick_params(axis="y", labelsize=12)
    ax.legend(fontsize=13)
    ax.set_title("이벤트별 정탐 / 오탐", fontsize=14, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def render_precision_event_table(events: list) -> str:
    active = [e for e in events if e["total"] > 0]
    if not active:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH}>이벤트</th>"
        f"<th {TH_C}>정탐</th><th {TH_C}>오탐</th>"
        f"<th {TH_C}>합계</th><th {TH_C}>오탐율 %</th></tr>"
    )
    for e in active:
        rate = e["odam_rate"]
        rc   = "#E45756" if rate > 30 else "#F58518" if rate > 15 else "inherit"
        html += (
            f"<tr><td {TD}><b>{e['event']}</b></td>"
            f"<td {TD_C} style='color:#4C78A8'>{e['jeongdam']:,}</td>"
            f"<td {TD_C} style='color:#E45756'>{e['odam']:,}</td>"
            f"<td {TD_C}>{e['total']:,}</td>"
            f"<td {TD_C}><b style='color:{rc}'>{rate}%</b></td></tr>"
        )
    html += "</table></div>"
    return html


def render_precision_node_table(nodes: list) -> str:
    if not nodes:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto;max-height:400px;overflow-y:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH}>Node ID</th><th {TH}>Name</th><th {TH_C}>Ch</th>"
        f"<th {TH_C}>정탐</th><th {TH_C}>오탐</th>"
        f"<th {TH_C}>합계</th><th {TH_C}>오탐율 %</th></tr>"
    )
    for n in nodes:
        rate = n["odam_rate"]
        rc   = "#E45756" if rate > 30 else "#F58518" if rate > 15 else "inherit"
        html += (
            f"<tr><td {TD}>{n['node_id']}</td>"
            f"<td {TD}>{n.get('node_name', '')}</td>"
            f"<td {TD_C}>{n['ch']}</td>"
            f"<td {TD_C} style='color:#4C78A8'>{n['jeongdam']:,}</td>"
            f"<td {TD_C} style='color:#E45756'>{n['odam']:,}</td>"
            f"<td {TD_C}>{n['total']:,}</td>"
            f"<td {TD_C}><b style='color:{rc}'>{rate}%</b></td></tr>"
        )
    html += "</table></div>"
    return html


def build_precision_trend(daily: list):
    """Günlük 오탐율 line chart + ortalama çizgisi."""
    fig, ax = plt.subplots(figsize=(20, 4))
    active = [d for d in daily if d["total"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels    = [f"{d['date'][5:]}({d['label']})" for d in daily]
    rates     = [d["odam_rate"] for d in daily]
    xs        = range(len(labels))
    total_od  = sum(d["odam"]  for d in daily)
    total_all = sum(d["total"] for d in daily)
    avg       = round(total_od / total_all * 100, 1) if total_all > 0 else 0

    ax.plot(xs, rates, marker="o", linewidth=2.5, markersize=6,
            color="#E45756", label="오탐율 %")
    ax.fill_between(xs, rates, alpha=0.10, color="#E45756")
    ax.axhline(y=avg, color="#F58518", linewidth=1.5, linestyle="--",
               label=f"평균 {avg:.1f}%")

    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=45, fontsize=11)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylabel("오탐율 %", fontsize=12)
    ax.set_title("일별 오탐율 추이", fontsize=14, pad=12)
    ax.legend(fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def build_precision_count_trend(daily: list):
    """정탐 vs 오탐 건수 두 선."""
    fig, ax = plt.subplots(figsize=(20, 4))
    active = [d for d in daily if d["total"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels = [f"{d['date'][5:]}({d['label']})" for d in daily]
    jd_v   = [d["jeongdam"] for d in daily]
    od_v   = [d["odam"]     for d in daily]
    xs     = range(len(labels))

    ax.plot(xs, jd_v, marker="o", linewidth=2.5, markersize=6,
            color="#4C78A8", label="정탐")
    ax.plot(xs, od_v, marker="o", linewidth=2.5, markersize=6,
            color="#E45756", label="오탐")
    ax.fill_between(xs, jd_v, alpha=0.08, color="#4C78A8")
    ax.fill_between(xs, od_v, alpha=0.08, color="#E45756")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=45, fontsize=11)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylabel("건수", fontsize=12)
    ax.set_title("일별 정탐 / 오탐 건수", fontsize=14, pad=12)
    ax.legend(fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


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


# ── 조희 렌더러 ───────────────────────────────────────────────────────────────

def render_stats(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    events = data.get("events", [])
    if not events:
        return "<p style='opacity:0.5'>결과 없음 / No results</p>"
    tr   = data["time_range"]
    html  = f"<h3>📅 {tr['start']} ~ {tr['end']}</h3>"
    html += "<table style='border-collapse:collapse;width:400px'>"
    html += f"<tr><th {TH}>Event / 이벤트</th><th {TH}>Count / 건수</th></tr>"
    for row in events:
        html += f"<tr><td {TD}>{row['event']}</td><td {TD_C}><b>{row['count']}</b></td></tr>"
    html += "</table>"
    return html


def render_list(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    records = data.get("records", [])
    if not records:
        return "<p style='opacity:0.5'>결과 없음 / No records</p>"

    html  = f"<p style='opacity:0.6'>{len(records)}건 조회됨</p>"
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr>"
        f"<th {TH}>Node ID</th><th {TH}>Name</th><th {TH_C}>Ch</th>"
        f"<th {TH}>Detect Time (+9h)</th>"
        f"<th {TH}>Event / 이벤트</th><th {TH_C}>Preview</th>"
        f"</tr>"
    )
    for r in records:
        if r.get("thumb_url"):
            img_tag = (
                f'<a href="{r["img_url"]}" target="_blank" title="클릭하여 원본 보기">'
                f'<img src="{r["thumb_url"]}" width="80" height="60" loading="lazy"'
                f' style="object-fit:cover;cursor:pointer;border-radius:3px;display:block"'
                f" onerror=\"this.parentElement.innerHTML='📷'\">"
                f'</a>'
            )
        else:
            img_tag = "<span style='opacity:0.4'>—</span>"

        html += (
            f"<tr>"
            f"<td {TD}>{r['node_id']}</td>"
            f"<td {TD}>{r.get('node_name', '')}</td>"
            f"<td {TD_C}>{r['ch']}</td>"
            f"<td {TD}>{r['dtct_dt']}</td>"
            f"<td {TD}>{r['event']}</td>"
            f"<td {TD_C}>{img_tag}</td>"
            f"</tr>"
        )
    html += "</table></div>"
    return html


def _node_btn_onclick(node_id: str, ch: str, start_dt: str, end_dt: str, events: list) -> str:
    api   = json.dumps(API_BASE_URL)
    nid   = json.dumps(node_id)
    ch_   = json.dumps(ch)
    sd    = json.dumps(start_dt)
    ed    = json.dumps(end_dt)
    evs   = json.dumps(events, ensure_ascii=False)
    th_s  = "border:1px solid rgba(128,128,128,0.4);padding:6px;background:rgba(128,128,128,0.15);font-weight:600"
    td_s  = "border:1px solid rgba(128,128,128,0.3);padding:6px"
    tdc_s = "border:1px solid rgba(128,128,128,0.3);padding:6px;text-align:center"

    js_lines = [
        "(async function(btn){",
        "  var b=btn.closest('tr').querySelector('.nd-result');",
        "  if(!b)return;",
        "  b.style.display='block';",
        "  b.innerHTML='<p>불러오는 중...</p>';",
        "  try{",
        f"    var p=new URLSearchParams({{node_id:{nid},ch:{ch_},start_dt:{sd},end_dt:{ed}}});",
        f"    {evs}.forEach(function(e){{p.append('events',e)}});",
        f"    var r=await fetch({api}+'/api/search/node-detail?'+p);",
        "    var d=await r.json();",
        f"    var h='<h4 style=\"margin:0 0 8px\">Node: <b>'+{nid}+'</b> / Ch: <b>'+{ch_}+'</b></h4>';",
        f"    var ts='{th_s}';",
        f"    var td='{td_s}';",
        f"    var tc='{tdc_s}';",
        "    if(d.events&&d.events.length){",
        "      h+='<table style=\"border-collapse:collapse\">';",
        "      h+='<tr><th style=\"'+ts+'\">Event</th><th style=\"'+ts+'\">Count</th></tr>';",
        "      d.events.forEach(function(e){",
        "        h+='<tr><td style=\"'+td+'\">'+e.event+'</td><td style=\"'+tc+'\"><b>'+e.count+'</b></td></tr>';",
        "      });",
        "      h+='</table>';",
        "    }else{h+='<p>데이터 없음</p>';}",
        "    b.innerHTML=h;",
        "  }catch(err){b.innerHTML='<p style=\"color:red\">오류: '+err.message+'</p>';}",
        "})(this);",
    ]
    return htmllib.escape("".join(js_lines))


def render_node_stats(data: dict, start_dt: str, end_dt: str, selected_events: list) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    nodes = data.get("nodes", [])
    if not nodes:
        return "<p style='opacity:0.5'>결과 없음 / No node data</p>"

    rows_html = ""
    for r in nodes:
        onclick = _node_btn_onclick(
            str(r["node_id"]), str(r["ch"]), start_dt, end_dt, selected_events
        )
        rows_html += (
            f"<tr>"
            f"<td {TD}>{r['node_id']}</td>"
            f"<td {TD_C}>{r['ch']}</td>"
            f"<td {TD_C}><b>{r['total']}</b></td>"
            f"<td {TD_C}>"
            f"<button onclick=\"{onclick}\""
            f" style='padding:4px 12px;cursor:pointer;border-radius:4px;"
            f"border:1px solid rgba(128,128,128,0.5);"
            f"background:rgba(128,128,128,0.1);font-size:13px'>"
            f"자세히 보기</button>"
            f"</td>"
            f"<td class='nd-result'"
            f" style='display:none;padding:8px;vertical-align:top;"
            f"border:1px solid rgba(128,128,128,0.3);border-radius:4px;min-width:160px'>"
            f"</td>"
            f"</tr>"
        )

    return (
        f"<table style='border-collapse:collapse;width:100%'>"
        f"<tr>"
        f"<th {TH}>Node ID</th><th {TH_C}>Channel</th>"
        f"<th {TH_C}>Total Events / 총 건수</th><th {TH_C}>Detail / 상세</th>"
        f"<th {TH_C}>결과</th>"
        f"</tr>"
        f"{rows_html}"
        f"</table>"
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


# ── 오탐 원인 렌더러 ──────────────────────────────────────────────────────────

_CAUSE_COLORS = ["#4C78A8", "#E45756", "#F58518", "#54A24B", "#B279A2",
                 "#9D755D", "#BAB0AC", "#72B7B2"]


def _cause_label(c: str) -> str:
    return c if c else "미입력"


def render_false_cause_completion(comp: dict) -> str:
    if not comp:
        return "<p style='opacity:0.5'>데이터 없음</p>"
    tot  = comp.get("total", 0)
    fill = comp.get("filled", 0);    fp = comp.get("filled_pct", 0)
    emp  = comp.get("empty",  0);    ep = comp.get("empty_pct",  0)
    null = comp.get("null_cnt", 0);  np_ = comp.get("null_pct",  0)

    def bar_html(pct, color):
        w = int(pct * 1.2)  # max ~120px at 100%
        return (f"<div style='display:inline-flex;align-items:center;gap:6px'>"
                f"<div style='width:{w}px;height:10px;background:{color};"
                f"border-radius:2px;opacity:0.75'></div>"
                f"<span style='font-size:0.85rem'>{pct}%</span></div>")

    html  = (f"<p style='opacity:0.6;margin:0 0 8px'>오탐 전체 <b>{tot:,}건</b> 중 "
             f"fls_pst_knd 입력 현황</p>")
    html += "<table style='border-collapse:collapse;font-size:13px'>"
    html += (
        f"<tr><th {TH}>구분</th><th {TH_C}>건수</th><th {TH}>비율</th></tr>"
        f"<tr><td {TD}><b style='color:#54A24B'>원인 입력됨</b></td>"
        f"<td {TD_C}>{fill:,}</td><td {TD}>{bar_html(fp,'#54A24B')}</td></tr>"
        f"<tr><td {TD}><b style='color:#F58518'>미입력 (빈 값)</b></td>"
        f"<td {TD_C}>{emp:,}</td><td {TD}>{bar_html(ep,'#F58518')}</td></tr>"
        f"<tr><td {TD}><b style='color:#BAB0AC'>NULL</b></td>"
        f"<td {TD_C}>{null:,}</td><td {TD}>{bar_html(np_,'#BAB0AC')}</td></tr>"
    )
    html += "</table>"
    return html


def build_false_cause_event_chart(events: list, all_causes: list):
    """이벤트별 grouped bar, hue = fls_pst_knd."""
    import numpy as np
    fig, ax = plt.subplots(figsize=(max(10, len(events) * 1.8), 6))
    if not events or not all_causes:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    n_ev  = len(events)
    n_c   = len(all_causes)
    x     = np.arange(n_ev)
    w     = min(0.7 / n_c, 0.25)

    ev_labels = [e["event"] for e in events]

    for i, cause in enumerate(all_causes):
        counts = [e["cause_counts"].get(cause, 0) for e in events]
        offset = (i - n_c / 2 + 0.5) * w
        color  = _CAUSE_COLORS[i % len(_CAUSE_COLORS)]
        bars   = ax.bar(x + offset, counts, w, label=_cause_label(cause),
                        color=color, alpha=0.85)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                        str(int(h)), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(ev_labels, fontsize=12)
    ax.set_ylabel("건수", fontsize=12)
    ax.set_title("이벤트별 오탐 원인 분포", fontsize=14, pad=12)
    ax.legend(fontsize=11, title="원인 (fls_pst_knd)", title_fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def render_false_cause_event_table(events: list, all_causes: list) -> str:
    if not events:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    header = f"<tr><th {TH}>이벤트</th>"
    for c in all_causes:
        header += f"<th {TH_C}>{_cause_label(c)}</th>"
    header += f"<th {TH_C}>합계</th></tr>"
    html += header

    for e in events:
        cc = e["cause_counts"]
        html += f"<tr><td {TD}><b>{e['event']}</b></td>"
        for c in all_causes:
            v = cc.get(c, 0)
            html += f"<td {TD_C}>{v:,}</td>"
        html += f"<td {TD_C}><b>{e['total']:,}</b></td></tr>"

    html += "</table></div>"
    return html


def render_false_cause_user_table(users: list, all_causes: list) -> str:
    if not users:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto;max-height:400px;overflow-y:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    header = f"<tr><th {TH}>사용자</th>"
    for c in all_causes:
        header += f"<th {TH_C}>{_cause_label(c)}</th>"
    header += f"<th {TH_C}>합계</th></tr>"
    html += header

    for u in users:
        cc = u["cause_counts"]
        html += f"<tr><td {TD}><b>{u['reg_id']}</b></td>"
        for c in all_causes:
            v = cc.get(c, 0)
            html += f"<td {TD_C}>{v:,}</td>"
        html += f"<td {TD_C}><b>{u['total']:,}</b></td></tr>"

    html += "</table></div>"
    return html


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


# ── 시간대 분석 렌더러 ────────────────────────────────────────────────────────

def render_time_dist_cards(cards: dict) -> str:
    if not cards:
        return "<p style='opacity:0.5'>데이터 없음</p>"
    bh  = cards.get("busiest_hr",   0)
    bc  = cards.get("busiest_cnt",  0)
    qh  = cards.get("quietest_hr",  0)
    qc  = cards.get("quietest_cnt", 0)
    nr  = cards.get("night_rate",   0)
    dr  = cards.get("day_rate",     0)
    tot = cards.get("total",        0)

    cs = "border-radius:10px;padding:16px 20px;text-align:center;flex:1;min-width:120px"
    return (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px'>"
        f"<div style='{cs};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2)'>"
        f"<div style='font-size:1.8rem;font-weight:700'>{tot:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>오탐 총계</div></div>"

        f"<div style='{cs};background:rgba(228,87,86,0.08);border:1px solid rgba(228,87,86,0.4)'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:#E45756'>{bh:02d}시</div>"
        f"<div style='font-size:0.85rem;font-weight:600;margin-top:2px'>가장 바쁜 시간</div>"
        f"<div style='font-size:0.8rem;opacity:0.5'>{bc:,}건</div></div>"

        f"<div style='{cs};background:rgba(84,162,75,0.08);border:1px solid rgba(84,162,75,0.4)'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:#54A24B'>{qh:02d}시</div>"
        f"<div style='font-size:0.85rem;font-weight:600;margin-top:2px'>가장 조용한 시간</div>"
        f"<div style='font-size:0.8rem;opacity:0.5'>{qc:,}건</div></div>"

        f"<div style='{cs};background:rgba(76,120,168,0.08);border:1px solid rgba(76,120,168,0.4)'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:#4C78A8'>{nr}%</div>"
        f"<div style='font-size:0.85rem;font-weight:600;margin-top:2px'>야간 비율</div>"
        f"<div style='font-size:0.8rem;opacity:0.5'>00 ~ 06시</div></div>"

        f"<div style='{cs};background:rgba(245,133,24,0.08);border:1px solid rgba(245,133,24,0.4)'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:#F58518'>{dr}%</div>"
        f"<div style='font-size:0.85rem;font-weight:600;margin-top:2px'>주간 비율</div>"
        f"<div style='font-size:0.8rem;opacity:0.5'>06 ~ 18시</div></div>"
        "</div>"
    )


def build_time_heatmap(hourly_events: dict):
    import numpy as np
    active_evs = [ev for ev in ALL_EVENTS if any(hourly_events.get(ev, []))]
    if not active_evs:
        fig, ax = plt.subplots(figsize=(20, 4))
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    matrix = np.array([hourly_events.get(ev, [0]*24) for ev in active_evs], dtype=float)
    h      = 5
    fig, ax = plt.subplots(figsize=(20, h))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    plt.colorbar(im, ax=ax, shrink=0.8, label="오탐 건수")

    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=10)
    ax.set_yticks(range(len(active_evs)))
    ax.set_yticklabels(active_evs, fontsize=11)
    ax.set_xlabel("시간 (hour)", fontsize=12)
    ax.set_title("시간대 × 이벤트 오탐 히트맵", fontsize=14, pad=12)

    # 값 표시
    for i in range(len(active_evs)):
        for j in range(24):
            v = int(matrix[i][j])
            if v > 0:
                ax.text(j, i, str(v), ha="center", va="center",
                        fontsize=8, color="black" if matrix[i][j] < matrix.max() * 0.6 else "white")
    fig.tight_layout()
    return fig


def build_time_slot_bar(slots: list):
    fig, ax = plt.subplots(figsize=(20, 5))
    if not slots:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    labels = [s["label"] for s in slots]
    counts = [s["count"] for s in slots]
    colors = ["#4C78A8", "#54A24B", "#F58518", "#B279A2"]

    bars = ax.bar(labels, counts, color=colors, alpha=0.85, width=0.55)
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + max(counts) * 0.01,
                    f"{int(h):,}", ha="center", va="bottom", fontsize=12)

    ax.set_title("시간대별 오탐 건수", fontsize=14, pad=12)
    ax.set_ylabel("건수", fontsize=12)
    ax.tick_params(axis="x", labelsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def build_time_line(hour_total: list):
    fig, ax = plt.subplots(figsize=(20, 5))
    active = [d for d in hour_total if d["count"] > 0]
    if not active:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    hours  = [d["hour"]  for d in hour_total]
    counts = [d["count"] for d in hour_total]
    total  = sum(counts)
    avg    = round(total / 24, 1)

    ax.plot(hours, counts, marker="o", linewidth=2.5, markersize=6,
            color="#E45756", label="오탐 건수")
    ax.fill_between(hours, counts, alpha=0.10, color="#E45756")
    ax.axhline(y=avg, color="#F58518", linewidth=1.5, linestyle="--",
               label=f"시간 평균 {avg:.1f}건")

    # 야간 배경
    ax.axvspan(0, 6,  alpha=0.06, color="#4C78A8", label="야간 00-06")
    ax.axvspan(18, 23, alpha=0.06, color="#B279A2", label="저녁 18-24")

    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}시" for h in hours], fontsize=10)
    ax.tick_params(axis="y", labelsize=11)
    ax.set_ylabel("건수", fontsize=12)
    ax.set_title("시간별 오탐 분포 (0~23시)", fontsize=14, pad=12)
    ax.legend(fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


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


# ── 기간별 조회 렌더러 ────────────────────────────────────────────────────────

def build_period_chart(data: dict):
    days = data.get("days", [])[-14:]  # last 14 days for chart
    fig, ax = plt.subplots(figsize=(14, 5))
    if not days:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    ref_date  = data.get("ref_date", "")
    time_from = data.get("time_from", "")
    time_to   = data.get("time_to", "")
    event_lbl = data.get("event", "전체")

    labels = [f"{d['date'][5:]} ({d['label']})" for d in days]
    counts = [d["count"] for d in days]
    colors = ["#E45756" if d["date"] == ref_date else "#4C78A8" for d in days]

    bars = ax.bar(range(len(labels)), counts, color=colors, alpha=0.85)
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + max(counts) * 0.01,
                    str(int(h)), ha="center", va="bottom", fontsize=10)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_title(
        f"이벤트 건수  [{time_from} ~ {time_to}]  ·  {event_lbl}  (최근 14일, 빨간색=기준일)",
        fontsize=13,
    )
    ax.set_ylabel("건수")
    fig.tight_layout()
    return fig


def render_period_list(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    days = data.get("days", [])
    if not days:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    ref_date  = data.get("ref_date", "")
    time_from = data.get("time_from", "")
    time_to   = data.get("time_to", "")
    event_lbl = data.get("event", "전체")

    html  = (f"<p style='opacity:0.6;margin:0 0 8px'>"
             f"📅 기준일: <b>{ref_date}</b> &nbsp;·&nbsp; "
             f"시간: <b>{time_from} ~ {time_to}</b> &nbsp;·&nbsp; "
             f"이벤트: <b>{event_lbl}</b></p>")
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH}>날짜</th><th {TH_C}>요일</th><th {TH_C}>건수</th></tr>"
    )

    max_cnt = max((d["count"] for d in days), default=1) or 1
    for d in reversed(days):  # newest first
        cnt  = d["count"]
        bg   = "background:rgba(228,87,86,0.12);" if d["date"] == ref_date else ""
        bw   = int(cnt / max_cnt * 80)
        bar  = (f"<div style='display:inline-flex;align-items:center;gap:6px'>"
                f"<b>{cnt}</b>"
                f"<div style='width:{bw}px;height:10px;background:#4C78A8;"
                f"border-radius:2px;opacity:0.7'></div></div>")
        html += (
            f"<tr style='{bg}'>"
            f"<td {TD}>{d['date']}</td>"
            f"<td {TD_C}>{d['label']}</td>"
            f"<td {TD_C}>{bar}</td>"
            f"</tr>"
        )
    html += "</table></div>"
    return html


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


# ── Gradio 레이아웃 ───────────────────────────────────────────────────────────

_now           = datetime.now()
_default_start = (_now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
_default_end   = _now.strftime("%Y-%m-%d %H:%M:%S")

_custom_css = """
#excel-upload { max-width: 260px; }
#excel-upload .wrap { min-height: 110px !important; padding: 10px 14px !important; }
#excel-upload label span { font-size: 12px !important; }
#import-btn { min-height: 110px !important; font-size: 15px !important; }
#import-col { max-width: 150px; }
"""

with gr.Blocks(title="Ainos Analytics", theme=gr.themes.Soft(), css=_custom_css) as app:

    with gr.Tabs() as tabs:

        # ── Tab 0: Home ──────────────────────────────────────────────────────
        with gr.Tab("🏠 Home", id=0):
            gr.HTML(
                "<div style='text-align:center;padding:48px 0 24px'>"
                "<div style='display:inline-block;"
                "background:#1a4fa3;color:#ffffff;"
                "font-size:1.6rem;font-weight:700;letter-spacing:0.18em;"
                "padding:6px 22px;border-radius:6px;margin-bottom:14px'>"
                "DANUSYS</div>"
                "<h1 style='font-size:2rem;margin-bottom:6px'>Ainos Platform</h1>"
                "</div>"
            )
            gr.HTML("""
                <style>
                  .home-card {
                    width:160px;height:160px;border-radius:14px;
                    display:flex;flex-direction:column;
                    align-items:center;justify-content:center;
                    gap:8px;cursor:pointer;user-select:none;transition:filter 0.2s;
                  }
                  .home-card:hover { filter: brightness(1.12); }
                </style>

                <!-- 1행: 매일 확인하는 것들 -->
                <div style="display:flex;justify-content:center;gap:20px;padding:16px 0 12px">

                  <div class="home-card"
                       style="border:2px solid rgba(99,190,123,0.6);background:rgba(99,190,123,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('오늘의')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">📊</span>
                    <span style="font-size:1rem;font-weight:600">오늘의 통계</span>
                    <span style="font-size:0.75rem;opacity:0.6">Today Stats</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(72,168,168,0.6);background:rgba(72,168,168,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('기간별')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">📆</span>
                    <span style="font-size:1rem;font-weight:600">기간별 조회</span>
                    <span style="font-size:0.75rem;opacity:0.6">Period Query</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(0,188,212,0.6);background:rgba(0,188,212,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('분석')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">📉</span>
                    <span style="font-size:1rem;font-weight:600">분석</span>
                    <span style="font-size:0.75rem;opacity:0.6">Analytics</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(100,149,237,0.6);background:rgba(100,149,237,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('조희')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">🔍</span>
                    <span style="font-size:1rem;font-weight:600">조희</span>
                    <span style="font-size:0.75rem;opacity:0.6">Search</span>
                  </div>

                </div>

                <!-- 2행: 주기적/관리용 -->
                <div style="display:flex;justify-content:center;gap:20px;padding:4px 0 32px">

                  <div class="home-card"
                       style="border:2px solid rgba(245,133,24,0.6);background:rgba(245,133,24,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('요약')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">📈</span>
                    <span style="font-size:1rem;font-weight:600">요약</span>
                    <span style="font-size:0.75rem;opacity:0.6">Summary</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(147,112,219,0.6);background:rgba(147,112,219,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('서버')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">🖥</span>
                    <span style="font-size:1rem;font-weight:600">서버 통계</span>
                    <span style="font-size:0.75rem;opacity:0.6">Server Stats</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(255,165,0,0.6);background:rgba(255,165,0,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('설정')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">⚙️</span>
                    <span style="font-size:1rem;font-weight:600">설정</span>
                    <span style="font-size:0.75rem;opacity:0.6">Settings</span>
                  </div>

                </div>
            """)

        # ── Tab 1: 오늘의 통계 ────────────────────────────────────────────────
        with gr.Tab("📊 오늘의 통계", id=1):
            gr.Markdown("## 오늘의 통계 / Today Stats")
            btn_refresh_today = gr.Button("🔄 새로고침", size="sm")
            today_out         = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")
            gr.Markdown("---")
            gr.Markdown("### 최근 14일 통계")
            histogram_out = gr.Plot(container=False)

        # ── Tab 2: 요약 ──────────────────────────────────────────────────────
        with gr.Tab("📈 요약", id=2):
            gr.Markdown("## 요약 / Summary")
            btn_refresh_summary = gr.Button("🔄 새로고침", size="sm")

            with gr.Tabs():
                with gr.Tab("🚶 행동 분석 (bhvr)"):
                    bhvr_sum_out    = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")
                    bhvr_line_out   = gr.Plot(container=False)
                    bhvr_detail_out = gr.HTML()

                with gr.Tab("🌊 재난 분석 (dst)"):
                    dst_sum_out    = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")
                    dst_line_out   = gr.Plot(container=False)
                    dst_detail_out = gr.HTML()

        # ── Tab 3: 서버 통계 ──────────────────────────────────────────────────
        with gr.Tab("🖥 서버 통계", id=3):
            gr.Markdown("## 지능형 서버 통계 / Server Stats")
            gr.Markdown("### 서버별 통계 (최근 14일)")
            btn_load_srv  = gr.Button("📊 통계 조회", variant="primary")
            srv_stats_out = gr.HTML("<p style='opacity:0.5'>위 버튼을 눌러 조회하세요</p>")
            srv_line_out  = gr.Plot(container=False, label="뷰어 비교 (line)")
            srv_hist_out  = gr.Plot(container=False, label="뷰어별 상세 (histogram)")

        # ── Tab 4: 조희 ──────────────────────────────────────────────────────
        with gr.Tab("🔍 조희", id=4):
            gr.Markdown("## 조희 / Search")

            with gr.Row():
                start_input = gr.Textbox(
                    label="Start / 시작",
                    value=_default_start,
                    placeholder="YYYY-MM-DD HH:MM:SS  또는  20260316000000",
                )
                end_input = gr.Textbox(
                    label="End / 종료",
                    value=_default_end,
                    placeholder="YYYY-MM-DD HH:MM:SS  또는  20260316235959",
                )

            node_id_input = gr.Textbox(
                label="Node ID 필터 (쉼표로 구분, 비워두면 전체)",
                placeholder="20882, 20883, 20884",
            )

            events_check = gr.CheckboxGroup(
                choices=ALL_EVENTS,
                value=ALL_EVENTS,
                label="Events / 이벤트",
            )

            with gr.Row():
                btn_all    = gr.Button("전체 선택 / Select All", size="sm")
                btn_clear  = gr.Button("전체 해제 / Clear All",  size="sm")
                btn_search = gr.Button("🔍 조희 / Search", variant="primary", scale=2)

            gr.Markdown("---")

            with gr.Tabs():
                with gr.Tab("📊 Stats / 통계"):
                    stats_out = gr.HTML("<p style='opacity:0.5'>조희 후 결과가 여기 표시됩니다.</p>")
                with gr.Tab("📋 List / 목록"):
                    list_out = gr.HTML("<p style='opacity:0.5'>조희 후 결과가 여기 표시됩니다.</p>")
                with gr.Tab("🖥 Node Stats / 노드 통계"):
                    node_stats_out = gr.HTML("<p style='opacity:0.5'>조희 후 결과가 여기 표시됩니다.</p>")

        # ── Tab 5: 분석 ──────────────────────────────────────────────────────
        with gr.Tab("📉 분석", id=5):
            gr.Markdown("## 분석 / Analytics")

            with gr.Tabs():

                # ── 처리 현황 ─────────────────────────────────────────────
                with gr.Tab("🔲 처리 현황"):
                    with gr.Row():
                        processing_period = gr.Radio(
                            choices=["오늘", "7일", "14일", "21일", "전체"],
                            value="전체",
                            label="기간",
                            interactive=True,
                        )
                        btn_processing = gr.Button("🔄 조회", variant="primary", scale=1)

                    processing_cards_out = gr.HTML("")

                    gr.Markdown("#### 이벤트별 처리 현황")
                    processing_bar_out = gr.Plot(container=False)

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("##### 이벤트별 상세")
                            processing_event_out = gr.HTML("")
                        with gr.Column():
                            gr.Markdown("##### 카메라별 미확인 순위")
                            processing_node_out = gr.HTML("")

                    gr.Markdown("#### 일별 미확인율 추이")
                    processing_trend_out = gr.Plot(container=False)
                    gr.Markdown("#### 일별 확인 완료 / 미확인 건수")
                    processing_count_trend_out = gr.Plot(container=False)

                # ── 정탐 / 오탐 ──────────────────────────────────────────
                with gr.Tab("✅ 정탐 / 오탐"):
                    with gr.Row():
                        precision_period = gr.Radio(
                            choices=["오늘", "7일", "14일", "21일", "전체"],
                            value="전체",
                            label="기간",
                            interactive=True,
                        )
                        btn_precision = gr.Button("🔄 조회", variant="primary", scale=1)

                    precision_cards_out = gr.HTML("")

                    gr.Markdown("#### 이벤트별 정탐 / 오탐")
                    precision_bar_out = gr.Plot(container=False)

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("##### 이벤트별 상세")
                            precision_event_out = gr.HTML("")
                        with gr.Column():
                            gr.Markdown("##### 카메라별 오탐 순위")
                            precision_node_out = gr.HTML("")

                    gr.Markdown("#### 일별 오탐율 추이")
                    precision_trend_out = gr.Plot(container=False)
                    gr.Markdown("#### 일별 정탐 / 오탐 건수")
                    precision_count_trend_out = gr.Plot(container=False)

                # ── 시간대 분석 ──────────────────────────────────────────
                with gr.Tab("🕐 시간대 분석"):
                    with gr.Row():
                        time_dist_period = gr.Radio(
                            choices=["오늘", "7일", "14일", "21일", "전체"],
                            value="전체",
                            label="기간",
                            interactive=True,
                        )
                        btn_time_dist = gr.Button("🔄 조회", variant="primary", scale=1)

                    time_dist_cards_out = gr.HTML("")

                    gr.Markdown("#### 시간대 × 이벤트 히트맵")
                    with gr.Row():
                        time_dist_heatmap_out = gr.Plot(container=False)

                    gr.Markdown("#### 시간별 분포 (0~23시)")
                    with gr.Row():
                        time_dist_line_out = gr.Plot(container=False)

                    gr.Markdown("#### 시간대별 건수")
                    with gr.Row():
                        time_dist_slot_out = gr.Plot(container=False)

                # ── 오탐 원인 ─────────────────────────────────────────────
                with gr.Tab("⚠️ 오탐 원인"):
                    with gr.Row():
                        false_cause_period = gr.Radio(
                            choices=["오늘", "7일", "14일", "21일", "전체"],
                            value="전체",
                            label="기간",
                            interactive=True,
                        )
                        btn_false_cause = gr.Button("🔄 조회", variant="primary", scale=1)

                    gr.Markdown("#### fls_pst_knd 입력 현황")
                    false_cause_completion_out = gr.HTML("")

                    gr.Markdown("#### 이벤트별 오탐 원인 분포")
                    false_cause_chart_out = gr.Plot(container=False)

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("##### 이벤트 × 원인 상세")
                            false_cause_event_out = gr.HTML("")
                        with gr.Column():
                            gr.Markdown("##### 사용자 × 원인 상세")
                            false_cause_user_out = gr.HTML("")

        # ── Tab 6: 설정 ──────────────────────────────────────────────────────
        with gr.Tab("⚙️ 설정", id=6):
            gr.Markdown("## 설정 / Settings")

            with gr.Tabs():
                with gr.Tab("📥 Excel 업로드"):
                    with gr.Row(equal_height=True):
                        excel_file  = gr.File(
                            label="Excel (.xlsx)",
                            file_types=[".xlsx"],
                            scale=0,
                            elem_id="excel-upload",
                        )
                        with gr.Column(scale=0, elem_id="import-col", min_width=140):
                            file_status = gr.HTML("")
                            btn_import  = gr.Button("📥 Import", variant="primary", elem_id="import-btn")
                        gr.HTML("")  # 나머지 공간 채우기 방지용
                    import_result = gr.HTML("")

                    gr.Markdown("---")
                    gr.Markdown("### 뷰어별 노드 목록")
                    viewer_radio = gr.Radio(
                        choices=[],
                        label="Viewer 선택",
                        interactive=True,
                    )
                    nodes_out = gr.HTML("<p style='opacity:0.5'>Import 후 표시됩니다</p>")

                    gr.Markdown("---")
                    gr.Markdown("### 수동 추가")
                    with gr.Row():
                        inp_viewer = gr.Textbox(label="Viewer Name",    placeholder="danuai56")
                        inp_node   = gr.Textbox(label="Node ID",         placeholder="NODE001")
                        inp_mgmt   = gr.Textbox(label="Management Code")
                        inp_name   = gr.Textbox(label="Name")
                    btn_add    = gr.Button("➕ 추가", variant="secondary")
                    add_result = gr.HTML("")

        # ── Tab 7: 기간별 조회 ────────────────────────────────────────────────
        with gr.Tab("📆 기간별 조회", id=7):
            gr.Markdown("## 기간별 조회 / Period Query")
            gr.Markdown(
                "특정 시간대의 이벤트 건수를 최근 14일 그래프와 30일 목록으로 조회합니다.\n\n"
                "> 예: 08:00~08:10 시간대를 기준으로 최근 14일 동안 매일 몇 건 발생했는지 한눈에 비교"
            )
            with gr.Row():
                pq_ref_date  = gr.Textbox(
                    label="기준 날짜",
                    value=datetime.now().strftime("%Y-%m-%d"),
                    placeholder="YYYY-MM-DD",
                    scale=2,
                )
                pq_time_from = gr.Textbox(
                    label="시작 시간",
                    value="00:00",
                    placeholder="HH:MM",
                    scale=1,
                )
                pq_time_to = gr.Textbox(
                    label="종료 시간",
                    value="23:59",
                    placeholder="HH:MM",
                    scale=1,
                )
                pq_event = gr.Dropdown(
                    choices=["전체"] + ALL_EVENTS,
                    value="전체",
                    label="이벤트 필터",
                    scale=2,
                )
                btn_pq = gr.Button("🔍 조회", variant="primary", scale=1, min_width=100)

            pq_chart_out = gr.Plot(container=False, label="14일 그래프")
            pq_list_out  = gr.HTML("<p style='opacity:0.5'>위 조건을 설정하고 조회 버튼을 누르세요</p>")

    # ── 이벤트 연결 ───────────────────────────────────────────────────────────

    _today_outs   = [today_out, histogram_out]
    _summary_outs = [bhvr_sum_out, bhvr_line_out, bhvr_detail_out,
                     dst_sum_out,  dst_line_out,  dst_detail_out]

    btn_refresh_today.click(load_today_tab,   outputs=_today_outs)
    btn_refresh_summary.click(load_summary_tab, outputs=_summary_outs)

    # 설정 탭 이벤트
    excel_file.change(
        lambda f: "<p style='color:green;margin:0'>✓ 파일 선택됨</p>" if f else "",
        inputs=[excel_file],
        outputs=[file_status],
    )
    btn_import.click(
        do_import_excel,
        inputs=[excel_file],
        outputs=[import_result, viewer_radio, nodes_out],
    )
    viewer_radio.change(
        do_load_nodes_by_viewer,
        inputs=[viewer_radio],
        outputs=[nodes_out],
    )
    btn_add.click(
        do_add_node,
        inputs=[inp_viewer, inp_node, inp_mgmt, inp_name],
        outputs=[add_result, nodes_out],
    )

    btn_load_srv.click(do_load_server_stats, outputs=[srv_stats_out, srv_line_out, srv_hist_out])

    _processing_outs = [
        processing_cards_out, processing_bar_out,
        processing_event_out, processing_node_out,
        processing_trend_out, processing_count_trend_out,
    ]
    btn_processing.click(do_load_processing, inputs=[processing_period], outputs=_processing_outs)
    processing_period.change(do_load_processing, inputs=[processing_period], outputs=_processing_outs)

    _precision_outs = [
        precision_cards_out, precision_bar_out,
        precision_event_out, precision_node_out,
        precision_trend_out, precision_count_trend_out,
    ]
    btn_precision.click(do_load_precision, inputs=[precision_period], outputs=_precision_outs)
    precision_period.change(do_load_precision, inputs=[precision_period], outputs=_precision_outs)

    _time_dist_outs = [
        time_dist_cards_out, time_dist_heatmap_out,
        time_dist_line_out,  time_dist_slot_out,
    ]
    btn_time_dist.click(do_load_time_dist, inputs=[time_dist_period], outputs=_time_dist_outs)
    time_dist_period.change(do_load_time_dist, inputs=[time_dist_period], outputs=_time_dist_outs)

    _false_cause_outs = [
        false_cause_completion_out, false_cause_chart_out,
        false_cause_event_out, false_cause_user_out,
    ]
    btn_false_cause.click(do_load_false_cause, inputs=[false_cause_period], outputs=_false_cause_outs)
    false_cause_period.change(do_load_false_cause, inputs=[false_cause_period], outputs=_false_cause_outs)

    btn_pq.click(
        do_period_query,
        inputs=[pq_ref_date, pq_time_from, pq_time_to, pq_event],
        outputs=[pq_chart_out, pq_list_out],
    )

    btn_all.click(  lambda: ALL_EVENTS, outputs=events_check)
    btn_clear.click(lambda: [],         outputs=events_check)
    btn_search.click(
        do_search,
        inputs=[start_input, end_input, events_check, node_id_input],
        outputs=[stats_out, list_out, node_stats_out],
    )

    app.load(load_today_tab,   outputs=_today_outs)
    app.load(load_summary_tab, outputs=_summary_outs)


if __name__ == "__main__":
    print("\n  UI  →  http://localhost:7860\n")
    app.launch(server_name="0.0.0.0", server_port=7860)
