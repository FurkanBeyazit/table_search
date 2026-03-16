import json
import gradio as gr
import requests
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

TH  = "style='border:1px solid rgba(128,128,128,0.4);padding:8px;background:rgba(128,128,128,0.15);text-align:left;font-weight:600'"
TD  = "style='border:1px solid rgba(128,128,128,0.3);padding:8px'"
TD_C = "style='border:1px solid rgba(128,128,128,0.3);padding:8px;text-align:center'"


def render_stats(data: dict) -> str:
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    events = data.get("events", [])
    if not events:
        return "<p style='color:#888'>결과 없음 / No results</p>"
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
        return "<p style='color:#888'>결과 없음 / No records</p>"

    html  = f"<p style='color:#555'>{len(records)}건 조회됨</p>"
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr>"
        f"<th {TH}>Node ID</th>"
        f"<th {TH}>Ch</th>"
        f"<th {TH}>Reg Time</th>"
        f"<th {TH}>Detect Time (+9h)</th>"
        f"<th {TH}>Event / 이벤트</th>"
        f"<th {TH}>Preview</th>"
        f"</tr>"
    )
    for r in records:
        if r["img_url"]:
            img_tag = (
                f'<a href="{r["img_url"]}" target="_blank" title="클릭하여 원본 보기">'
                f'<img src="{r["img_url"]}" width="80" height="60" '
                f'style="object-fit:cover;cursor:pointer;border-radius:3px" '
                f"onerror=\"this.parentElement.innerHTML='📷'\">"
                f'</a>'
            )
        else:
            img_tag = "<span style='color:#bbb'>—</span>"

        html += (
            f"<tr>"
            f"<td {TD}>{r['node_id']}</td>"
            f"<td {TD_C}>{r['ch']}</td>"
            f"<td {TD}>{r['reg_dt']}</td>"
            f"<td {TD}>{r['dtct_dt']}</td>"
            f"<td {TD}>{r['event']}</td>"
            f"<td {TD_C}>{img_tag}</td>"
            f"</tr>"
        )
    html += "</table></div>"
    return html


def render_node_stats(data: dict, start_dt: str, end_dt: str, selected_events: list) -> str:
    """
    Node istatistik tablosu + her satırda '자세히 보기' butonu.
    Buton tıklandığında JS doğrudan FastAPI'yi çağırır,
    sonucu aynı HTML bloğu içindeki div'e yazar — Gradio callback gerekmez.
    """
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    nodes = data.get("nodes", [])
    if not nodes:
        return "<p style='color:#888'>결과 없음 / No node data</p>"

    rows_html = ""
    for r in nodes:
        node_id_js = json.dumps(str(r["node_id"]))
        ch_js      = json.dumps(str(r["ch"]))
        rows_html += (
            f"<tr>"
            f"<td {TD}>{r['node_id']}</td>"
            f"<td {TD_C}>{r['ch']}</td>"
            f"<td {TD_C}><b>{r['total']}</b></td>"
            f"<td {TD_C}>"
            f"  <button onclick=\"showNodeDetail({node_id_js},{ch_js})\" "
            f"    style='padding:4px 12px;cursor:pointer;border-radius:4px;"
            f"           border:1px solid #aaa;background:#f7f7f7;font-size:13px'>"
            f"    자세히 보기"
            f"  </button>"
            f"</td>"
            f"</tr>"
        )

    # JS 변수들을 JSON으로 안전하게 embed
    events_js   = json.dumps(selected_events)
    start_js    = json.dumps(start_dt)
    end_js      = json.dumps(end_dt)
    api_base_js = json.dumps(API_BASE_URL)

    return f"""
    <table style='border-collapse:collapse;width:100%'>
      <tr>
        <th {TH}>Node ID</th>
        <th {TH}>Channel</th>
        <th {TH}>Total Events / 총 건수</th>
        <th {TH}>Detail / 상세</th>
      </tr>
      {rows_html}
    </table>

    <div id="node-detail-box"
         style="margin-top:16px;padding:12px;border:1px solid #e0e0e0;
                border-radius:6px;display:none">
    </div>

    <script>
    (function() {{
      const _events  = {events_js};
      const _start   = {start_js};
      const _end     = {end_js};
      const _apiBase = {api_base_js};

      window.showNodeDetail = async function(nodeId, ch) {{
        const box = document.getElementById('node-detail-box');
        box.style.display = 'block';
        box.innerHTML = '<p style="color:#888">불러오는 중...</p>';

        const p = new URLSearchParams({{node_id: nodeId, ch: ch, start_dt: _start, end_dt: _end}});
        _events.forEach(e => p.append('events', e));

        try {{
          const resp = await fetch(`${{_apiBase}}/api/search/node-detail?${{p}}`);
          const d    = await resp.json();

          let html = `<h4 style="margin:0 0 8px">🖥 Node: <b>${{nodeId}}</b> &nbsp;/&nbsp; Ch: <b>${{ch}}</b></h4>`;
          if (!d.events || d.events.length === 0) {{
            html += '<p style="color:#888">데이터 없음</p>';
          }} else {{
            html += '<table style="border-collapse:collapse">';
            html += '<tr><th style="border:1px solid rgba(128,128,128,0.4);padding:6px;background:rgba(128,128,128,0.15);font-weight:600">Event</th>'
                  + '<th style="border:1px solid rgba(128,128,128,0.4);padding:6px;background:rgba(128,128,128,0.15);font-weight:600">Count</th></tr>';
            for (const e of d.events) {{
              html += `<tr>`
                    + `<td style="border:1px solid rgba(128,128,128,0.3);padding:6px">${{e.event}}</td>`
                    + `<td style="border:1px solid rgba(128,128,128,0.3);padding:6px;text-align:center"><b>${{e.count}}</b></td>`
                    + `</tr>`;
            }}
            html += '</table>';
          }}
          box.innerHTML = html;
        }} catch(err) {{
          box.innerHTML = `<p style="color:red">오류: ${{err.message}}</p>`;
        }}
      }};
    }})();
    </script>
    """


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

with gr.Blocks(title="Security Analytics Platform", theme=gr.themes.Soft()) as app:

    # ── Home ──────────────────────────────────────────────────────────────────
    with gr.Tabs() as tabs:
        with gr.Tab("🏠 Home", id=0):
            gr.Markdown("# Security Analytics Platform\n### 보안 분석 플랫폼")
            gr.Markdown("---")
            with gr.Row():
                home_search_btn = gr.Button("🔍\n\n조희\nSearch",   scale=1, size="lg")
                gr.Button(       "📊\n\nReports\n보고서",           scale=1, size="lg", interactive=False)
                gr.Button(       "⚙️\n\nSettings\n설정",           scale=1, size="lg", interactive=False)

        # ── Search / 조희 ─────────────────────────────────────────────────────
        with gr.Tab("🔍 조희", id=1):
            gr.Markdown("## 조희 / Search")

            with gr.Row():
                start_input = gr.Textbox(
                    label="Start / 시작",
                    value=_default_start,
                    placeholder="YYYY-MM-DD HH:MM:SS",
                )
                end_input = gr.Textbox(
                    label="End / 종료",
                    value=_default_end,
                    placeholder="YYYY-MM-DD HH:MM:SS",
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

            # ── 결과 탭 ───────────────────────────────────────────────────────
            with gr.Tabs():
                with gr.Tab("📊 Stats / 통계"):
                    stats_out = gr.HTML("<p style='color:#aaa'>조희 후 결과가 여기 표시됩니다.</p>")

                with gr.Tab("📋 List / 목록"):
                    list_out = gr.HTML("<p style='color:#aaa'>조희 후 결과가 여기 표시됩니다.</p>")

                with gr.Tab("🖥 Node Stats / 노드 통계"):
                    node_stats_out = gr.HTML("<p style='color:#aaa'>조희 후 결과가 여기 표시됩니다.</p>")

    # ── Wiring ────────────────────────────────────────────────────────────────
    home_search_btn.click(lambda: gr.Tabs(selected=1), outputs=tabs)

    btn_all.click(  lambda: ALL_EVENTS, outputs=events_check)
    btn_clear.click(lambda: [],         outputs=events_check)

    btn_search.click(
        do_search,
        inputs=[start_input, end_input, events_check],
        outputs=[stats_out, list_out, node_stats_out],
    )


if __name__ == "__main__":
    print("\n  UI  →  http://localhost:7860\n")
    app.launch(server_name="0.0.0.0", server_port=7860)
