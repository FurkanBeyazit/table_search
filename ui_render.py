import json
import html as htmllib
import gradio as gr
import requests
from config import ALL_EVENTS, BHVR_EVENTS, DST_EVENTS, API_BASE_URL, VLM_EVENTS

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


def _vlm_btn_onclick(node_id, ch, dtct_dt, event, img_path, cam_name, mgmt_code, dst_val):
    api    = json.dumps(API_BASE_URL)
    p_node = json.dumps(str(node_id))
    p_ch   = json.dumps(str(ch))
    p_dt   = json.dumps(str(dtct_dt))
    p_ev   = json.dumps(str(event))
    p_img  = json.dumps(str(img_path or ""))
    p_cam  = json.dumps(str(cam_name or ""))
    p_mgmt = json.dumps(str(mgmt_code or ""))
    dst_js = "null" if dst_val is None else str(dst_val)

    js_lines = [
        "(async function(btn){",
        "if(btn._excelDataUrl){var a=document.createElement('a');a.href=btn._excelDataUrl;a.download=btn._excelFilename||'event_report.xlsx';a.click();return;}",
        "btn.disabled=true;",
        "btn.textContent='⏳ 생성 중...';",
        "btn.style.cssText='font-size:11px;padding:3px 8px;background:#555;color:#fff;border:none;border-radius:3px;white-space:nowrap';",
        f"var p=new URLSearchParams({{node_id:{p_node},ch:{p_ch},dtct_dt:{p_dt},event_type:{p_ev},img_path:{p_img},cam_name:{p_cam},mgmt_code:{p_mgmt}}});",
        f"var dst={dst_js};",
        "if(dst!==null&&dst!==undefined)p.append('dst_val',String(dst));",
        "var re=document.getElementById('vlm-js-result');",
        "try{",
        f"var r=await fetch({api}+'/api/search/vlm-report?'+p,{{signal:AbortSignal.timeout(120000)}});",
        "if(!r.ok)throw new Error('API '+r.status+': '+await r.text());",
        "var data=await r.json();",
        "if(re){",
        "var rj=data.report_json||{};",
        "var obs=data.observation_text||'';",
        "var rep=(typeof rj['보고자']==='object'&&rj['보고자'])||{};",
        "var h='<div style=\"font-size:13px;line-height:1.8;padding:10px 12px;background:rgba(21,101,192,.08);border-left:3px solid #1565c0;border-radius:0 6px 6px 0;margin-top:8px\">';",
        "['사고 발생일시','장소','사고 관제내용','피해 우려사항','관제센터 조치사항','그 외 특이사항'].forEach(function(k){if(rj[k])h+='<b>'+k+':</b> '+rj[k]+'<br>';});",
        "if(obs)h+='<b>관찰 내용:</b> '+obs+'<br>';",
        "if(rep['성명'])h+='<b>보고자:</b> '+rep['성명']+' / '+(rep['근무조']||'')+'<br>';",
        "h+='</div>';",
        "re.innerHTML=h;",
        "}",
        f"var er=await fetch({api}+'/api/search/vlm-excel',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}});",
        "if(er.ok){",
        "var blob=await er.blob();",
        "var cd=er.headers.get('Content-Disposition')||'';",
        "var m=cd.match(/filename\\*=UTF-8''([^;\\s]+)/i)||cd.match(/filename=[\"']?([^\"';\\n]+)[\"']?/);",
        "var fname=m?decodeURIComponent(m[1]):'event_report.xlsx';",
        "var reader=new FileReader();",
        "reader.onload=function(){btn._excelDataUrl=reader.result;btn._excelFilename=fname;var a=document.createElement('a');a.href=reader.result;a.download=fname;a.click()};",
        "reader.readAsDataURL(blob);",
        "}",
        "btn.textContent='✅ 생성됨';",
        "btn.style.cssText='font-size:11px;padding:3px 8px;background:#2e7d32;color:#fff;border:none;border-radius:3px;white-space:nowrap';",
        "btn.disabled=false;",
        "}catch(e){",
        "if(re)re.innerHTML='<p style=\"color:red;font-size:13px\">⚠ '+e.message+'</p>';",
        "btn.disabled=false;",
        "btn.textContent='📋 보고서 생성';",
        "btn.style.cssText='font-size:11px;padding:3px 8px;background:#1565c0;color:#fff;border:none;border-radius:3px;white-space:nowrap';",
        "}",
        "})(this);"
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
    has_mi = "mihagin" in summary          # 처리현황(get_precision) → 전체+미확인, 기간별 → eski
    mi     = summary.get("mihagin", 0)

    cs = "border-radius:10px;padding:18px 24px;text-align:center;flex:1;min-width:110px"
    total_label = "전체" if has_mi else "검토 완료"

    mi_card = (
        f"<div style='{cs};background:rgba(245,133,24,0.08);border:1px solid rgba(245,133,24,0.4)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#F58518'>{mi:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>미확인</div></div>"
    ) if has_mi else ""

    return (
        "<div style='display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px'>"
        f"<div style='{cs};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.2)'>"
        f"<div style='font-size:2rem;font-weight:700'>{total:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>{total_label}</div></div>"

        f"<div style='{cs};background:rgba(76,120,168,0.08);border:1px solid rgba(76,120,168,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#4C78A8'>{jd:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>정탐</div></div>"

        f"<div style='{cs};background:rgba(228,87,86,0.08);border:1px solid rgba(228,87,86,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#E45756'>{od:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>오탐</div></div>"

        f"{mi_card}"

        f"<div style='{cs};background:rgba(84,162,75,0.08);border:1px solid rgba(84,162,75,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#54A24B'>{prec}%</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>Precision</div></div>"
        "</div>"
    )


def render_precision_event_table(events: list) -> str:
    active = [e for e in events if e.get("event_total", e.get("total", 0)) > 0]
    if not active:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    html  = "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH}>이벤트</th>"
        f"<th {TH_C}>정탐</th><th {TH_C}>오탐</th><th {TH_C}>미확인</th>"
        f"<th {TH_C}>합계</th><th {TH_C}>오탐율 %</th></tr>"
    )
    for e in active:
        rate  = e["odam_rate"]
        rc    = "#E45756" if rate > 30 else "#F58518" if rate > 15 else "inherit"
        total = e.get("event_total", e.get("total", 0))   # 합계 = ham 전체
        mi    = e.get("mihagin", 0)
        html += (
            f"<tr><td {TD}><b>{e['event']}</b></td>"
            f"<td {TD_C} style='color:#4C78A8'>{e['jeongdam']:,}</td>"
            f"<td {TD_C} style='color:#E45756'>{e['odam']:,}</td>"
            f"<td {TD_C} style='color:#F58518'>{mi:,}</td>"
            f"<td {TD_C}><b>{total:,}</b></td>"
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


def render_list(data: dict, generated_keys=None) -> str:
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
        f"<th {TH_C}>보고서</th>"
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

        if r.get("event") in VLM_EVENTS:
            onclick = _vlm_btn_onclick(
                r["node_id"], r["ch"], r["dtct_dt"], r["event"],
                r.get("img_path") or "", r.get("node_name") or "",
                r.get("mgmt_code") or "", r.get("dst_val"),
            )
            report_cell = (
                f"<button onclick=\"{onclick}\""
                f" style='font-size:11px;padding:3px 8px;cursor:pointer;"
                f"background:#1565c0;color:#fff;border:none;"
                f"border-radius:3px;white-space:nowrap'>📋 보고서 생성</button>"
            )
        else:
            report_cell = "<span style='opacity:0.3'>—</span>"

        html += (
            f"<tr>"
            f"<td {TD}>{r['node_id']}</td>"
            f"<td {TD}>{r.get('node_name', '')}</td>"
            f"<td {TD_C}>{r['ch']}</td>"
            f"<td {TD}>{r['dtct_dt']}</td>"
            f"<td {TD}>{r['event']}</td>"
            f"<td {TD_C}>{img_tag}</td>"
            f"<td {TD_C}>{report_cell}</td>"
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
    if not monthly:
        return "<p style='opacity:0.5'>데이터 없음</p>"

    start = monthly[0]
    end   = monthly[-1]
    title = f"📅 최근 12개월 ({start['year']}.{start['month']}월 ~ {end['year']}.{end['month']}월)"
    html  = f"<h4 style='margin:20px 0 8px'>{title}</h4>"
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

    prev_year = None
    for m in reversed(monthly):
        # 연도가 바뀌는 시점에 구분선
        if prev_year and m["year"] != prev_year:
            html += (
                f"<tr><td colspan='5' "
                f"style='text-align:center;font-size:0.75rem;opacity:0.5;"
                f"padding:4px;border-top:2px solid rgba(128,128,128,0.3)'>"
                f"── {m['year']}년 ──</td></tr>"
            )
        prev_year = m["year"]

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


def render_mihagin_summary(data: dict) -> str:
    """미확인 요약: 상단 카드 + event별 미확인 건수/비율 테이블."""
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"

    summary = data.get("summary", {})
    events  = data.get("events", [])
    df, dt  = data.get("date_from", ""), data.get("date_to", "")
    period  = df if df == dt else f"{df} ~ {dt}"

    total  = summary.get("total", 0)
    bhvr   = summary.get("bhvr_total", 0)
    dst    = summary.get("dst_total", 0)
    ev_all = summary.get("event_count_total", 0)
    rate   = summary.get("overall_rate", 0.0)

    cs = "border-radius:10px;padding:18px 24px;text-align:center;flex:1;min-width:120px"
    cards = (
        f"<p style='opacity:0.6;margin:0 0 10px'>📅 {period} &nbsp;·&nbsp; "
        f"전체 원본 <b>{ev_all:,}</b>건 중 미확인</p>"
        "<div style='display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px'>"

        f"<div style='{cs};background:rgba(245,133,24,0.08);border:1px solid rgba(245,133,24,0.4)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#F58518'>{total:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>총 미확인</div></div>"

        f"<div style='{cs};background:rgba(76,120,168,0.08);border:1px solid rgba(76,120,168,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#4C78A8'>{bhvr:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>행동 (BHAR)</div></div>"

        f"<div style='{cs};background:rgba(84,162,75,0.08);border:1px solid rgba(84,162,75,0.35)'>"
        f"<div style='font-size:2rem;font-weight:700;color:#54A24B'>{dst:,}</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>재난 (CALAMITY)</div></div>"

        f"<div style='{cs};background:rgba(128,128,128,0.06);border:1px solid rgba(128,128,128,0.2)'>"
        f"<div style='font-size:2rem;font-weight:700'>{rate}%</div>"
        f"<div style='font-size:0.8rem;opacity:0.6;margin-top:4px'>전체 미확인율</div></div>"
        "</div>"
    )

    if not events:
        return cards + "<p style='opacity:0.5'>해당 기간 미확인 이벤트 없음</p>"

    rows = ""
    for e in events:
        er = e["event_rate"]
        rc = "#E45756" if er > 30 else "#F58518" if er > 15 else "inherit"
        badge = ("background:rgba(76,120,168,0.15);color:#4C78A8" if e["category"] == "BHAR"
                 else "background:rgba(84,162,75,0.15);color:#54A24B")
        rows += (
            f"<tr><td {TD}><b>{htmllib.escape(str(e['event']))}</b>"
            f" <span style='{badge};font-size:0.68rem;padding:1px 6px;border-radius:8px;"
            f"margin-left:4px'>{e['category']}</span></td>"
            f"<td {TD_C}><b style='color:#F58518'>{e['mihagin']:,}</b></td>"
            f"<td {TD_C}>{e['total']:,}</td>"
            f"<td {TD_C}><b style='color:{rc}'>{er}%</b></td>"
            f"<td {TD_C}>{e['share']}%</td></tr>"
        )

    table = (
        "<div style='overflow-x:auto'>"
        "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
        f"<tr><th {TH}>이벤트</th><th {TH_C}>미확인</th><th {TH_C}>전체</th>"
        f"<th {TH_C}>미확인율</th><th {TH_C}>점유율</th></tr>"
        f"{rows}</table></div>"
    )
    return cards + table


def render_mihagin_list(data: dict) -> str:
    """미확인 상세 목록: 미리보기 + 시간 + 이벤트 + 카메라 + 장소 + 채널."""
    if "error" in data:
        return f"<p style='color:red'>⚠ {data['error']}</p>"
    records = data.get("records", [])
    if not records:
        return "<p style='opacity:0.5'>미확인 목록 없음</p>"

    total = data.get("summary", {}).get("total", 0)
    page  = data.get("page", 1)
    size  = data.get("size", 50)
    shown = len(records)
    first = (page - 1) * size + 1
    last  = (page - 1) * size + shown

    html  = (f"<p style='opacity:0.6;margin:0 0 8px'>총 <b>{total:,}</b>건 중 "
             f"{first:,}~{last:,}번 표시</p>")
    html += "<div style='overflow-x:auto'>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += (
        f"<tr><th {TH_C}>미리보기</th><th {TH}>시간</th><th {TH}>이벤트</th>"
        f"<th {TH}>카메라</th><th {TH_C}>노드_채널</th></tr>"
    )
    for r in records:
        if r.get("thumb_url"):
            img_tag = (
                f'<a href="{r["img_url"]}" target="_blank" title="원본 보기">'
                f'<img src="{r["thumb_url"]}" width="80" height="60" loading="lazy"'
                f' style="object-fit:cover;cursor:pointer;border-radius:3px;display:block"'
                f" onerror=\"this.parentElement.innerHTML='📷'\"></a>"
            )
        else:
            img_tag = "<span style='opacity:0.4'>—</span>"

        cam   = htmllib.escape(str(r.get("node_name") or "")) or "<span style='opacity:0.4'>—</span>"
        nid    = htmllib.escape(str(r.get("node_id") or ""))
        ch_raw = r.get("ch")                       # 0 da geçerli değer (or '' ile yutma!)
        chv    = htmllib.escape(str(ch_raw).strip()) if ch_raw is not None else ""
        node_ch = f"{nid}_{chv}" if (nid and chv != "") else (nid or chv or "—")
        ev    = htmllib.escape(str(r.get("event") or ""))

        html += (
            f"<tr><td {TD_C}>{img_tag}</td>"
            f"<td {TD}>{r.get('time_str', '')}</td>"
            f"<td {TD}>{ev}</td>"
            f"<td {TD}>{cam}</td>"
            f"<td {TD_C}>{node_ch}</td></tr>"
        )
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


def render_precision_period_breakdown(ev_day: dict, days: list) -> str:
    """이벤트 başına: gün×정오탐 tablosu + gömülü line chart (base64 PNG).
    Sadece veri olan event'ler, ALL_EVENTS sırasında. Tek HTML string döner."""
    from datetime import date as _date
    from ui_charts import build_precision_period_event_png

    KR = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}

    if not ev_day or not days:
        return "<p style='opacity:0.5'>해당 기간 데이터 없음</p>"

    blocks = []
    for ev in ALL_EVENTS:
        series = ev_day.get(ev)
        if not series:
            continue
        tot = sum(int(v.get("jeongdam", 0)) + int(v.get("odam", 0)) for v in series.values())
        if tot <= 0:
            continue

        html = f"<h4 style='margin:18px 0 8px'>{ev}</h4>"
        html += "<div style='overflow-x:auto'><table style='border-collapse:collapse;width:100%;font-size:13px'>"
        html += (
            f"<tr><th {TH}>날짜</th><th {TH_C}>요일</th>"
            f"<th {TH_C}>정탐</th><th {TH_C}>오탐</th><th {TH_C}>오탐율 %</th></tr>"
        )
        for d in days:
            cell = series.get(d) or {}
            j = int(cell.get("jeongdam", 0))
            o = int(cell.get("odam", 0))
            t = j + o
            rate = round(o / t * 100, 1) if t > 0 else 0.0
            rc = "#E45756" if rate > 30 else "#F58518" if rate > 15 else "inherit"
            wd = KR[_date.fromisoformat(d).weekday()]
            html += (
                f"<tr><td {TD}>{d}</td><td {TD_C}>{wd}</td>"
                f"<td {TD_C} style='color:#4C78A8'>{j:,}</td>"
                f"<td {TD_C} style='color:#E45756'>{o:,}</td>"
                f"<td {TD_C}><b style='color:{rc}'>{rate}%</b></td></tr>"
            )
        html += "</table></div>"

        img = build_precision_period_event_png(ev, days, series)
        html += f"<img src='{img}' style='width:100%;margin:6px 0 4px'/>"
        blocks.append(html)

    if not blocks:
        return "<p style='opacity:0.5'>해당 기간 데이터 없음</p>"
    return "".join(blocks)


# ════════════════════════════════════════════════════════════════════════════
# 릴리즈 노트 — 단일 소스 (single source of truth)
# ▶ 새 기능/수정 배포 시 여기만 수정:
#   1) RN_RELEASES 맨 앞에 새 블록 추가  (version, date=YYYY-MM-DD, new[], fix[])
#   2) RN_APP_VERSION 을 같은 버전으로 올림  → 홈 알림 점이 다시 켜짐
# 항목 형식: "짧은 제목 — 상세 설명"  ('이전 버전' 영역은 '—' 앞 짧은 제목만 표시)
# RN_RECENT_DAYS(약 3개월) 지난 블록은 자동으로 '이전 버전'으로 내려간다.
# ════════════════════════════════════════════════════════════════════════════
RN_APP_VERSION = "4.6"
RN_RECENT_DAYS = 90

RN_RELEASES = [
    {
        "version": "4.6",
        "date": "2026-06-23",
        "new": [
            "미확인 분석 탭 추가 — 운영자가 정탐/오탐 판정을 하지 않은 미처리 이벤트를 조회",
            "조회 목록에서 이벤트 탐지 보고서 생성 버튼 추가 (화재·침수·쓰러짐)",
            "처리 현황 — 일자 / 기간 두 가지 통계로 분리, 기간별 추이 분석 제공",
            "기간별 조회 탭 추가 — 특정 시간대를 최근 14일과 비교",
            "운영자 분석 탭 추가 — 운영자별 정탐/오탐 추이 및 처리 비중",
            "월간 보고서 · 이벤트 현황 Excel 내보내기 (파일명에 타임스탬프 자동 적용)",
        ],
        "fix": [
            "오늘의 통계 히트맵 차트가 표시되지 않던 문제 수정",
            "조회 Node ID 필터링 정확도 개선",
            "보고서 생성 오류 처리(에러 핸들링) 개선",
            "UI 라벨 정리 (조희 → 조회) 및 푸터 개선",
        ],
    },
    # 다음 배포 예시:
    # {"version": "4.7", "date": "2026-07-01",
    #  "new": ["새 기능 짧은 제목 — 상세 설명"], "fix": []},
]


def render_release_notes() -> str:
    """홈 화면 우상단 'Release Notes' 배지 + 모달.

    내용은 위의 RN_RELEASES(단일 소스)에서 읽는다. RN_RECENT_DAYS 가 지난 버전은
    자동으로 '이전 버전(Older Versions)' 영역으로 내려가 짧은 제목만 표시된다.

    Gradio 주의: gr.HTML 안의 <script> 는 실행되지 않으므로 모든 내용은 여기
    Python 에서 미리 렌더링하고, 상호작용은 inline onclick / <img onload> 로 처리한다.
    """
    from datetime import date, datetime

    version = RN_APP_VERSION
    today   = date.today()

    def _days(ds: str) -> int:
        return (today - datetime.strptime(ds, "%Y-%m-%d").date()).days

    recent = [r for r in RN_RELEASES if _days(r["date"]) <= RN_RECENT_DAYS]
    older  = [r for r in RN_RELEASES if _days(r["date"]) >  RN_RECENT_DAYS]

    def _items(arr) -> str:
        return "".join(f"<li>{htmllib.escape(str(x))}</li>" for x in arr)

    body = ""
    # 최근 버전: 버전마다 별도 블록(버전 헤더 + 자체 What's New / Fix), 최신이 맨 위
    for idx, r in enumerate(recent):
        tag = "<span class='rn-rel-new'>NEW</span>" if idx == 0 else ""
        body += (
            f"<div class='rn-rel'><div class='rn-rel-head'>v{htmllib.escape(str(r['version']))}"
            f"<span class='rn-rel-date'>{htmllib.escape(str(r['date']))}</span>{tag}</div>"
        )
        if r.get("new"):
            body += f"<div class='rn-sec rn-new'>✨ What's New</div><ul class='rn-list'>{_items(r['new'])}</ul>"
        if r.get("fix"):
            body += f"<div class='rn-sec rn-fix'>🛠 Fix</div><ul class='rn-list'>{_items(r['fix'])}</ul>"
        body += "</div>"
    if not recent:
        body += "<p style='opacity:0.5;font-size:0.9rem'>최근 업데이트 없음</p>"

    if older:
        body += ("<div class='rn-older-head' "
                 "onclick=\"this.nextElementSibling.classList.toggle('rn-open')\">"
                 "📦 이전 버전 (Older Versions) ▾</div><div class='rn-older-body'>")
        for r in older:
            shorts = [str(x).split(" — ")[0] for x in (r.get("new", []) + r.get("fix", []))]
            body += (
                f"<div class='rn-ov'><div class='rn-vh'>v{htmllib.escape(str(r['version']))}"
                f"<span class='rn-d'>{htmllib.escape(str(r['date'])[:7])}</span></div>"
                f"<ul class='rn-list'>{_items(shorts)}</ul></div>"
            )
        body += "</div>"

    # 색상은 Gradio 테마 변수(var)에 연결 → 라이트/다크 자동 대응. fallback은 라이트값.
    css = """<style>
#rnBadge{position:absolute;top:6px;right:6px;display:inline-flex;align-items:center;gap:7px;
  background:#1a4fa3;border:1px solid #1a4fa3;color:#fff;font-size:.85rem;font-weight:600;
  padding:7px 14px;border-radius:20px;cursor:pointer;box-shadow:0 2px 8px rgba(26,79,163,.28);
  transition:transform .15s;z-index:5}
#rnBadge:hover{transform:translateY(-1px)}
#rnBadge .rn-dot{display:block;width:8px;height:8px;border-radius:50%;background:#ef4444;animation:rnPulse 1.8s infinite}
html.rn-seen #rnBadge .rn-dot{display:none}
@keyframes rnPulse{0%{box-shadow:0 0 0 0 rgba(239,68,68,.6)}70%{box-shadow:0 0 0 8px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
.rn-overlay{display:none;position:fixed;inset:0;z-index:9999;background:rgba(17,22,29,.45);
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
  align-items:flex-start;justify-content:center;padding:48px 16px}
.rn-overlay.rn-show{display:flex}
.rn-modal{width:min(480px,100%);max-height:84vh;overflow:auto;
  background:var(--block-background-fill,#fff);color:var(--body-text-color,#1f2937);
  border:1px solid var(--border-color-primary,rgba(128,128,128,.25));
  border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,.45)}
.rn-modal-head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;
  border-bottom:1px solid var(--border-color-primary,rgba(128,128,128,.25));position:sticky;top:0;
  background:var(--block-background-fill,#fff);border-radius:14px 14px 0 0}
.rn-modal-ttl{font-size:1.1rem;font-weight:700;color:var(--body-text-color,#1f2937)}
.rn-modal-ver{font-size:.72rem;color:var(--body-text-color-subdued,#6b7280);font-weight:600;margin-left:6px}
.rn-modal-x{cursor:pointer;font-size:1.2rem;color:var(--body-text-color-subdued,#6b7280);border:none;background:none;line-height:1}
.rn-modal-body{padding:6px 22px 22px}
.rn-rel + .rn-rel{border-top:1px solid var(--border-color-primary,rgba(128,128,128,.2));margin-top:12px;padding-top:4px}
.rn-rel-head{display:flex;align-items:center;gap:8px;margin:14px 0 2px;font-size:.98rem;font-weight:700;color:var(--body-text-color,#1f2937)}
.rn-rel-date{font-size:.72rem;font-weight:500;color:var(--body-text-color-subdued,#6b7280)}
.rn-rel-new{font-size:.62rem;font-weight:700;letter-spacing:.04em;background:#16a34a;color:#fff;padding:1px 7px;border-radius:9px}
.rn-sec{font-size:.9rem;font-weight:700;margin:12px 0 8px}
.rn-sec.rn-new{color:#3b82f6}
.rn-sec.rn-fix{color:#f59e0b}
.rn-list{list-style:none;margin:0;padding:0}
.rn-list li{position:relative;padding:5px 0 5px 18px;font-size:.9rem;line-height:1.55;color:var(--body-text-color,#374151)}
.rn-list li::before{content:"•";position:absolute;left:4px;color:var(--body-text-color-subdued,#9ca3af)}
.rn-older-head{margin-top:22px;padding-top:14px;border-top:1px solid var(--border-color-primary,rgba(128,128,128,.25));
  font-size:.85rem;font-weight:700;color:var(--body-text-color-subdued,#6b7280);cursor:pointer;user-select:none}
.rn-older-body{display:none;margin-top:8px}
.rn-older-body.rn-open{display:block}
.rn-ov{padding:7px 0;border-bottom:1px dashed var(--border-color-primary,rgba(128,128,128,.25))}
.rn-ov:last-child{border-bottom:none}
.rn-vh{font-size:.8rem;font-weight:700;color:var(--body-text-color,#374151)}
.rn-vh .rn-d{font-weight:400;color:var(--body-text-color-subdued,#6b7280);margin-left:6px}
.rn-ov .rn-list{margin:3px 0 0}
.rn-ov .rn-list li{font-size:.82rem;color:var(--body-text-color-subdued,#6b7280);padding:3px 0 3px 16px;line-height:1.45}
.rn-ov .rn-list li::before{color:var(--body-text-color-subdued,#cbd5e1)}
</style>"""

    # Nokta her açılışta yanıp söner; tıklayınca o oturum için durur (kalıcılık yok).
    open_js = (
        "(function(btn){document.documentElement.classList.add('rn-seen');"
        "var o=document.getElementById('rnOverlay');if(o)o.classList.add('rn-show');})(this)"
    )

    badge = (
        "<div style='position:relative;height:0'>"
        f"<div id='rnBadge' onclick=\"{open_js}\">"
        "<span class='rn-dot'></span>🔔 Release Notes</div>"
        "</div>"
    )

    modal = (
        "<div id='rnOverlay' class='rn-overlay' "
        "onclick=\"if(event.target===this)this.classList.remove('rn-show')\">"
        "<div class='rn-modal'><div class='rn-modal-head'>"
        f"<span class='rn-modal-ttl'>Release Notes <span class='rn-modal-ver'>v{htmllib.escape(version)}</span></span>"
        "<button class='rn-modal-x' "
        "onclick=\"var o=document.getElementById('rnOverlay');if(o)o.classList.remove('rn-show')\">✕</button>"
        f"</div><div class='rn-modal-body'>{body}</div></div></div>"
    )

    return css + badge + modal
