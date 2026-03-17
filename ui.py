import json
import html as htmllib
import gradio as gr
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
from datetime import datetime, timedelta
from config import ALL_EVENTS, API_BASE_URL


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── HTML renderers ────────────────────────────────────────────────────────────

TH   = "style='border:1px solid rgba(128,128,128,0.4);padding:8px;background:rgba(128,128,128,0.15);text-align:left;font-weight:600'"
TD   = "style='border:1px solid rgba(128,128,128,0.3);padding:8px'"
TD_C = "style='border:1px solid rgba(128,128,128,0.3);padding:8px;text-align:center'"


def render_stats(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    events = data.get("events", [])
    if not events:
        return "<p style='opacity:0.5'>결과 없음 / No results</p>"
    tr = data["time_range"]
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
        f"<th {TH}>Node ID</th><th {TH}>Ch</th>"
        f"<th {TH}>Reg Time</th><th {TH}>Detect Time (+9h)</th>"
        f"<th {TH}>Event / 이벤트</th><th {TH}>Preview</th>"
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
            f"<td {TD}>{r['node_id']}</td><td {TD_C}>{r['ch']}</td>"
            f"<td {TD}>{r['reg_dt']}</td><td {TD}>{r['dtct_dt']}</td>"
            f"<td {TD}>{r['event']}</td><td {TD_C}>{img_tag}</td>"
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
        "(async function(){",
        "  var b=document.getElementById('nd-result');",
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
        "})();",
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
            f"</tr>"
        )

    return (
        f"<table style='border-collapse:collapse;width:100%'>"
        f"<tr>"
        f"<th {TH}>Node ID</th>"
        f"<th {TH}>Channel</th>"
        f"<th {TH}>Total Events / 총 건수</th>"
        f"<th {TH}>Detail / 상세</th>"
        f"</tr>"
        f"{rows_html}"
        f"</table>"
        f"<div id='nd-result'"
        f" style='margin-top:14px;padding:12px;"
        f"border:1px solid rgba(128,128,128,0.3);"
        f"border-radius:6px;display:none'></div>"
    )


# ── Stats tab renderers ───────────────────────────────────────────────────────

def render_today_events(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    events = data.get("events", [])
    if not events:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    d     = data.get("date", "")
    as_of = data.get("as_of", "")
    html  = f"<p style='opacity:0.6;margin:0 0 8px'>📅 {d} &nbsp;·&nbsp; {as_of} 기준</p>"
    html += "<table style='border-collapse:collapse;width:360px'>"
    html += f"<tr><th {TH}>이벤트</th><th {TH}>건수</th></tr>"
    for row in events:
        html += f"<tr><td {TD}>{row['event']}</td><td {TD_C}><b>{row['count']}</b></td></tr>"
    html += "</table>"
    return html


def render_summary(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"

    as_of = data.get("as_of", "")
    date  = data.get("date", "")

    def tbl(title: str, counts: dict) -> str:
        t  = f"<h4 style='margin:0 0 6px'>{title}</h4>"
        t += "<table style='border-collapse:collapse;width:320px;margin-bottom:16px'>"
        t += f"<tr><th {TH}>기간</th><th {TH}>건수</th></tr>"
        t += f"<tr><td {TD}>오늘</td><td {TD_C}><b>{counts.get('today', 0)}</b></td></tr>"
        t += f"<tr><td {TD}>최근 7일</td><td {TD_C}><b>{counts.get('last_7d', 0)}</b></td></tr>"
        t += f"<tr><td {TD}>최근 30일</td><td {TD_C}><b>{counts.get('last_30d', 0)}</b></td></tr>"
        t += "</table>"
        return t

    html  = f"<p style='opacity:0.6;margin:0 0 12px'>📅 {date} &nbsp;·&nbsp; {as_of} 기준</p>"
    html += tbl("🚶 행동 분석 (bhvr)", data.get("bhvr", {}))
    html += tbl("🌊 재난 분석 (dst)", data.get("dst", {}))
    return html


def build_histogram(data: dict):
    fig, ax = plt.subplots(figsize=(20, 10))
    if "error" in data or not data.get("days"):
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.axis("off")
        return fig

    days = data["days"]
    labels = [f"{d['date'][5:]}({d['label']})" for d in days]

    all_ev = []
    seen = set()
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
    ax.set_title("최근 14일 행동 분석 이벤트", fontsize=18, pad=20)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def load_stats_tab():
    today_html  = render_today_events(api_get("/api/stats/today",     {}))
    summary_html = render_summary(api_get("/api/stats/summary",  {}))
    histogram    = build_histogram(api_get("/api/stats/histogram", {}))
    return today_html, summary_html, histogram


# ── Search logic ──────────────────────────────────────────────────────────────

def do_search(start_dt: str, end_dt: str, selected_events: list):
    if not selected_events:
        msg = "<p style='color:orange'>⚠ 이벤트를 하나 이상 선택하세요</p>"
        return msg, msg, msg

    params = {"start_dt": start_dt, "end_dt": end_dt, "events": selected_events}

    stats_html = render_stats(api_get("/api/search/stats", params))
    list_html  = render_list(api_get("/api/search/list",   params))
    node_html  = render_node_stats(
        api_get("/api/search/node-stats", params),
        start_dt, end_dt, selected_events,
    )
    return stats_html, list_html, node_html


# ── Gradio layout ─────────────────────────────────────────────────────────────

_now           = datetime.now()
_default_start = (_now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
_default_end   = _now.strftime("%Y-%m-%d %H:%M:%S")

with gr.Blocks(title="Danusys Security Analytics", theme=gr.themes.Soft()) as app:

    with gr.Tabs() as tabs:
        with gr.Tab("🏠 Home", id=0):
            gr.HTML(
                "<div style='text-align:center;padding:48px 0 24px'>"
                "<p style='opacity:0.4;font-size:0.9rem;margin:0 0 4px;letter-spacing:0.12em'>DANUSYS</p>"
                "<h1 style='font-size:2rem;margin-bottom:6px'>Security Analytics Platform</h1>"
                "<p style='opacity:0.5;font-size:1rem'>보안 분석 플랫폼</p>"
                "</div>"
            )
            gr.HTML("""
                <div style="display:flex;justify-content:center;gap:24px;padding:8px 0 32px">

                  <div onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('통계')){tabs[i].click();return;}} })()"
                       style="width:180px;height:180px;border-radius:14px;
                              border:2px solid rgba(99,190,123,0.6);
                              background:rgba(99,190,123,0.08);
                              display:flex;flex-direction:column;
                              align-items:center;justify-content:center;
                              gap:10px;cursor:pointer;user-select:none;
                              transition:background 0.2s"
                       onmouseover="this.style.background='rgba(99,190,123,0.18)'"
                       onmouseout="this.style.background='rgba(99,190,123,0.08)'">
                    <span style="font-size:2.4rem">📊</span>
                    <span style="font-size:1.1rem;font-weight:600">통계</span>
                    <span style="font-size:0.8rem;opacity:0.6">Statistics</span>
                  </div>

                  <div onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('조희')){tabs[i].click();return;}} })()"
                       style="width:180px;height:180px;border-radius:14px;
                              border:2px solid rgba(100,149,237,0.6);
                              background:rgba(100,149,237,0.08);
                              display:flex;flex-direction:column;
                              align-items:center;justify-content:center;
                              gap:10px;cursor:pointer;user-select:none;
                              transition:background 0.2s"
                       onmouseover="this.style.background='rgba(100,149,237,0.18)'"
                       onmouseout="this.style.background='rgba(100,149,237,0.08)'">
                    <span style="font-size:2.4rem">🔍</span>
                    <span style="font-size:1.1rem;font-weight:600">조희</span>
                    <span style="font-size:0.8rem;opacity:0.6">Search</span>
                  </div>

                  <div style="width:180px;height:180px;border-radius:14px;
                              border:2px dashed rgba(128,128,128,0.25);
                              display:flex;flex-direction:column;
                              align-items:center;justify-content:center;
                              gap:10px;opacity:0.3;cursor:not-allowed">
                    <span style="font-size:2.4rem">⚙️</span>
                    <span style="font-size:1.1rem;font-weight:600">설정</span>
                    <span style="font-size:0.8rem">Settings</span>
                  </div>

                </div>
            """)

        with gr.Tab("📊 통계", id=2):
            gr.Markdown("## 통계 / Statistics")

            with gr.Tabs():
                with gr.Tab("오늘의 통계"):
                    today_out = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")

                with gr.Tab("요약 / Summary"):
                    summary_out = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")

                with gr.Tab("히스토그램 / Histogram"):
                    histogram_out = gr.Plot(label="최근 14일 행동 분석 이벤트",
                                           container=False)

        with gr.Tab("🔍 조희", id=1):
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

    btn_all.click(  lambda: ALL_EVENTS, outputs=events_check)
    btn_clear.click(lambda: [],         outputs=events_check)
    btn_search.click(
        do_search,
        inputs=[start_input, end_input, events_check],
        outputs=[stats_out, list_out, node_stats_out],
    )

    app.load(
        load_stats_tab,
        outputs=[today_out, summary_out, histogram_out],
    )


if __name__ == "__main__":
    print("\n  UI  →  http://localhost:7860\n")
    app.launch(server_name="0.0.0.0", server_port=7860,) #share=True
