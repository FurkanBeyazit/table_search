import json
import html as htmllib
import gradio as gr
import requests
from config import ALL_EVENTS, BHVR_EVENTS, DST_EVENTS, API_BASE_URL

TH   = "style='border:1px solid rgba(128,128,128,0.4);padding:8px;background:rgba(128,128,128,0.15);text-align:left;font-weight:600'"
TH_C = "style='border:1px solid rgba(128,128,128,0.4);padding:8px;background:rgba(128,128,128,0.15);text-align:center;font-weight:600'"
TD   = "style='border:1px solid rgba(128,128,128,0.3);padding:8px'"
TD_C = "style='border:1px solid rgba(128,128,128,0.3);padding:8px;text-align:center'"


def _cause_label(c: str) -> str:
    return c if c else "미입력"


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


def render_summary_counts(summary: dict, title: str) -> str:
    html  = f"<h4 style='margin:0 0 8px'>{title}</h4>"
    html += "<table style='border-collapse:collapse;width:300px'>"
    html += f"<tr><th {TH}>기간</th><th {TH}>건수</th></tr>"
    html += f"<tr><td {TD}>오늘</td><td {TD_C}><b>{summary.get('today', 0)}</b></td></tr>"
    html += f"<tr><td {TD}>최근 7일</td><td {TD_C}><b>{summary.get('last_7d', 0)}</b></td></tr>"
    html += f"<tr><td {TD}>최근 30일</td><td {TD_C}><b>{summary.get('last_30d', 0)}</b></td></tr>"
    html += "</table>"
    return html


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


def render_time_dist_cards(cards: dict, total_label: str = "오탐 총계") -> str:
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
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>{total_label}</div></div>"

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


def render_operator_monthly_table(data: dict) -> str:
    monthly = data.get("monthly", [])
    year    = data.get("year", "")
    if not monthly:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = f"<h4 style='margin:20px 0 8px'>📅 {year}년 월별 현황</h4>"
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%'>"
    html += (
        f"<tr>"
        f"<th {TH}>월</th>"
        f"<th {TH_C}>합계</th>"
        f"<th {TH_C} style='color:#4C78A8'>정탐</th>"
        f"<th {TH_C} style='color:#E45756'>오탐</th>"
        f"<th {TH_C}>오탐률</th>"
        f"</tr>"
    )

    for m in monthly:
        total = m.get("total", 0)
        j     = m.get("jeongdam", 0)
        o     = m.get("odam", 0)
        rate  = round(o / total * 100, 1) if total > 0 else 0.0
        fade  = " style='opacity:0.35'" if total == 0 else ""
        html += (
            f"<tr{fade}>"
            f"<td {TD}><b>{m['month']}월</b></td>"
            f"<td {TD_C}><b>{total}</b></td>"
            f"<td {TD_C} style='color:#4C78A8'>{j}</td>"
            f"<td {TD_C} style='color:#E45756'>{o}</td>"
            f"<td {TD_C}>{rate}%</td>"
            f"</tr>"
        )

    html += "</table></div>"
    return html


def render_operator_30day_table(data: dict) -> str:
    days = data.get("days", [])
    if not days:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%'>"
    html += (
        f"<tr>"
        f"<th {TH}>날짜</th>"
        f"<th {TH_C}>요일</th>"
        f"<th {TH_C}>총계</th>"
        f"<th {TH_C} style='color:#4C78A8'>정탐</th>"
        f"<th {TH_C} style='color:#E45756'>오탐</th>"
        f"<th {TH_C}>원인 미입력</th>"
        f"</tr>"
    )

    for day in days:
        evs = day.get("events", {})
        j   = sum(v.get("jeongdam", 0) for v in evs.values())
        o   = sum(v.get("odam",     0) for v in evs.values())
        t   = j + o
        mii = day.get("miipryeok", 0)
        fade = " style='opacity:0.35'" if t == 0 else ""
        html += (
            f"<tr{fade}>"
            f"<td {TD}>{day['date']}</td>"
            f"<td {TD_C}>{day['label']}</td>"
            f"<td {TD_C}><b>{t}</b></td>"
            f"<td {TD_C} style='color:#4C78A8'>{j}</td>"
            f"<td {TD_C} style='color:#E45756'>{o}</td>"
            f"<td {TD_C}>{mii}</td>"
            f"</tr>"
        )

    html += "</table></div>"
    return html


def render_operator_table(data: dict, highlight_reg_id: str = None) -> str:
    operators    = data.get("operators", [])
    avg_odam     = data.get("avg_odam_rate", 0.0)
    avg_per      = data.get("avg_per_person", 0.0)
    date_range   = data.get("date_range", "")

    if not operators:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    cs = "border-radius:10px;padding:12px 18px;text-align:center;min-width:140px"
    summary_html = (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px'>"
        f"<div style='{cs};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2)'>"
        f"<div style='font-size:1.6rem;font-weight:700'>{data.get('total_operators',0)}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>운영자 수</div></div>"

        f"<div style='{cs};background:rgba(76,120,168,0.08);border:1px solid rgba(76,120,168,0.4)'>"
        f"<div style='font-size:1.6rem;font-weight:700;color:#4C78A8'>{avg_per:,.1f}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>인당 평균 처리</div></div>"

        f"<div style='{cs};background:rgba(228,87,86,0.08);border:1px solid rgba(228,87,86,0.4)'>"
        f"<div style='font-size:1.6rem;font-weight:700;color:#E45756'>{avg_odam}%</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>전체 평균 오탐률</div></div>"

        f"<div style='{cs};background:rgba(128,128,128,0.05);border:1px solid rgba(128,128,128,0.15)'>"
        f"<div style='font-size:0.85rem;font-weight:600;margin-top:6px'>📅 {date_range}</div>"
        f"<div style='font-size:0.75rem;opacity:0.5;margin-top:4px'>최근 30일</div></div>"
        "</div>"
    )

    html  = summary_html
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%'>"
    html += (
        f"<tr>"
        f"<th {TH}>운영자</th>"
        f"<th {TH_C}>총계</th>"
        f"<th {TH_C}>정탐</th>"
        f"<th {TH_C}>오탐</th>"
        f"<th {TH_C}>원인 미입력</th>"
        f"<th {TH_C}>처리 비중</th>"
        f"<th {TH_C}>오탐률</th>"
        f"<th {TH_C}>오탐률 비교</th>"
        f"</tr>"
    )

    total_all = sum(op["total"] for op in operators) or 1

    for op in operators:
        rate      = op["odam_rate"]
        share     = round(op["total"] / total_all * 100, 1)
        diff      = round(rate - avg_odam, 1)

        # color based on odam_rate vs average
        if rate > avg_odam:
            row_color   = "rgba(228,87,86,0.07)"
            badge_color = "#E45756"
            arrow = f"▲ +{diff}%"
        else:
            row_color   = "rgba(76,120,168,0.07)"
            badge_color = "#4C78A8"
            arrow = f"▼ {diff}%"

        if highlight_reg_id and op["reg_id"] == highlight_reg_id:
            row_style = f"style='background:rgba(255,193,7,0.15);border-left:3px solid #FFC107'"
        else:
            row_style = f"style='background:{row_color}'"

        html += (
            f"<tr {row_style}>"
            f"<td {TD}><b>{op['reg_id']}</b></td>"
            f"<td {TD_C}>{op['total']:,}</td>"
            f"<td {TD_C}>{op['jeongdam']:,}</td>"
            f"<td {TD_C}>{op['odam']:,}</td>"
            f"<td {TD_C}>{op['miipryeok']:,}</td>"
            f"<td {TD_C}>{share}%</td>"
            f"<td {TD_C}><b>{rate}%</b></td>"
            f"<td {TD_C}><span style='color:{badge_color};font-weight:600'>{arrow}</span></td>"
            f"</tr>"
        )

    html += "</table></div>"
    return html


def render_operator_daily_table(data: dict) -> str:
    days_30 = data.get("days", [])
    days_14 = days_30[-14:]

    if not days_14:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto;margin-top:12px'>"
    html += "<table style='border-collapse:collapse;width:100%'>"

    # 헤더
    html += f"<tr><th {TH} style='min-width:60px'>구분</th>"
    for day in days_14:
        date_label = day["date"][5:]  # MM-DD
        kr_label   = day["label"]
        html += (
            f"<th {TH_C} style='min-width:54px'>"
            f"{date_label}<br>"
            f"<span style='font-size:0.72rem;opacity:0.55'>{kr_label}</span>"
            f"</th>"
        )
    html += "</tr>"

    # 정탐
    html += f"<tr><td {TD}><b style='color:#4C78A8'>정탐</b></td>"
    for day in days_14:
        j = sum(v.get("jeongdam", 0) for v in day.get("events", {}).values())
        html += f"<td {TD_C}>{j}</td>"
    html += "</tr>"

    # 오탐
    html += f"<tr><td {TD}><b style='color:#E45756'>오탐</b></td>"
    for day in days_14:
        o = sum(v.get("odam", 0) for v in day.get("events", {}).values())
        html += f"<td {TD_C}>{o}</td>"
    html += "</tr>"

    # 합계
    html += f"<tr style='background:rgba(128,128,128,0.06)'><td {TD}><b>합계</b></td>"
    for day in days_14:
        evs   = day.get("events", {})
        total = sum(v.get("jeongdam", 0) + v.get("odam", 0) for v in evs.values())
        html += f"<td {TD_C}><b>{total}</b></td>"
    html += "</tr>"

    html += "</table></div>"
    return html


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
