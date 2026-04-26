import gradio as gr
from datetime import datetime, timedelta
from config import ALL_EVENTS, BHVR_EVENTS, DST_EVENTS, API_BASE_URL

from ui_charts import (build_histogram, build_line_chart, build_server_line,
    build_server_histogram, build_precision_bar, build_precision_trend,
    build_precision_count_trend, build_false_cause_event_chart, build_time_heatmap,
    build_time_slot_bar, build_time_line, build_period_chart,
    build_operator_chart_trend)
from ui_render import (render_today_events, render_summary_counts, render_detail_table,
    render_nodes_table, render_server_stats, render_precision_cards,
    render_precision_event_table, render_precision_node_table, render_stats, render_list,
    render_node_stats, render_false_cause_completion, render_false_cause_event_table,
    render_false_cause_user_table, render_time_dist_cards, render_period_list,
    render_operator_table)
from ui_handlers import (api_get, load_today_tab, load_summary_tab, get_viewer_names,
    do_load_nodes_by_viewer, do_import_excel, do_add_node, do_load_server_stats,
    do_load_precision, do_search, do_load_false_cause,
    do_load_time_dist_all, do_load_time_dist, do_period_query,
    do_load_operator_init, do_load_operator_chart, do_load_operator_detail,
    do_export_bhvr, do_export_dst, do_export_list, do_generate_monthly_report)

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

                  <div class="home-card"
                       style="border:2px solid rgba(34,139,34,0.6);background:rgba(34,139,34,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('Report')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.2rem">📄</span>
                    <span style="font-size:1rem;font-weight:600">Report</span>
                    <span style="font-size:0.75rem;opacity:0.6">Monthly Excel</span>
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
                    with gr.Row(equal_height=True):
                        gr.Markdown("#### 30일 상세")
                        btn_export_bhvr  = gr.Button("📥 Excel", size="sm", scale=0, min_width=90)
                    bhvr_export_file = gr.File(label="", visible=False, interactive=False)
                    bhvr_detail_out  = gr.HTML()

                with gr.Tab("🌊 재난 분석 (dst)"):
                    dst_sum_out    = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")
                    dst_line_out   = gr.Plot(container=False)
                    with gr.Row(equal_height=True):
                        gr.Markdown("#### 30일 상세")
                        btn_export_dst  = gr.Button("📥 Excel", size="sm", scale=0, min_width=90)
                    dst_export_file = gr.File(label="", visible=False, interactive=False)
                    dst_detail_out  = gr.HTML()

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
                    with gr.Row(equal_height=True):
                        gr.Markdown("#### 목록")
                        btn_export_list  = gr.Button("📥 Excel", size="sm", scale=0, min_width=90)
                    list_export_file = gr.File(label="", visible=False, interactive=False)
                    list_out = gr.HTML("<p style='opacity:0.5'>조희 후 결과가 여기 표시됩니다.</p>")
                with gr.Tab("🖥 Node Stats / 노드 통계"):
                    node_stats_out = gr.HTML("<p style='opacity:0.5'>조희 후 결과가 여기 표시됩니다.</p>")

        # ── Tab 5: 분석 ──────────────────────────────────────────────────────
        with gr.Tab("📉 분석", id=5):
            gr.Markdown("## 분석 / Analytics")

            with gr.Tabs():

                # ── 처리 현황 ─────────────────────────────────────────────
                with gr.Tab("✅ 처리 현황"):
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

                    with gr.Accordion("📊 전체 이벤트 시간 분석", open=False):
                        with gr.Row():
                            time_all_period = gr.Radio(
                                choices=["오늘", "7일", "14일", "21일", "전체"],
                                value="전체",
                                label="기간",
                                interactive=True,
                            )
                            btn_time_all = gr.Button("🔄 조회", variant="primary", scale=1)

                        time_all_cards_out = gr.HTML("")

                        gr.Markdown("#### 시간대 × 이벤트 히트맵 (전체)")
                        with gr.Row():
                            time_all_heatmap_out = gr.Plot(container=False)

                        gr.Markdown("#### 시간별 이벤트 분포 (0~23시)")
                        with gr.Row():
                            time_all_line_out = gr.Plot(container=False)

                        gr.Markdown("#### 시간대별 건수")
                        with gr.Row():
                            time_all_slot_out = gr.Plot(container=False)

                    with gr.Accordion("⚠️ 오탐 시간 분석", open=False):
                        with gr.Row():
                            time_dist_period = gr.Radio(
                                choices=["오늘", "7일", "14일", "21일", "전체"],
                                value="전체",
                                label="기간",
                                interactive=True,
                            )
                            btn_time_dist = gr.Button("🔄 조회", variant="primary", scale=1)

                        time_dist_cards_out = gr.HTML("")

                        gr.Markdown("#### 시간대 × 이벤트 오탐 히트맵")
                        with gr.Row():
                            time_dist_heatmap_out = gr.Plot(container=False)

                        gr.Markdown("#### 시간별 오탐 분포 (0~23시)")
                        with gr.Row():
                            time_dist_line_out = gr.Plot(container=False)

                        gr.Markdown("#### 시간대별 오탐 건수")
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

                # ── 운영자 분석 ───────────────────────────────────────────
                with gr.Tab("👤 운영자 분석"):
                    with gr.Tabs():

                        with gr.Tab("📈 운영자 분석"):
                            with gr.Row():
                                operator_select = gr.Dropdown(
                                    choices=[],
                                    label="운영자 선택",
                                    interactive=True,
                                    scale=4,
                                )
                                btn_operator = gr.Button("🔄 조회", variant="primary", scale=1)
                            operator_chart_out = gr.Plot(container=False)
                            gr.Markdown("#### 일별 정탐 / 오탐 (최근 14일)")
                            operator_daily_table_out   = gr.HTML("")
                            operator_monthly_table_out = gr.HTML("")

                        with gr.Tab("📋 운영자 상세 분석"):
                            with gr.Row():
                                operator_detail_select = gr.Dropdown(
                                    choices=["전체 보기"],
                                    label="운영자 선택",
                                    interactive=True,
                                    scale=4,
                                )
                                btn_operator_detail = gr.Button("🔄 조회", variant="primary", scale=1)
                            operator_table_out = gr.HTML("")

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
                    _init_viewers = get_viewer_names()
                    _init_first   = _init_viewers[0] if _init_viewers else None
                    viewer_radio = gr.Radio(
                        choices=_init_viewers,
                        value=_init_first,
                        label="Viewer 선택",
                        interactive=True,
                    )
                    nodes_out = gr.HTML(
                        do_load_nodes_by_viewer(_init_first) if _init_first
                        else "<p style='opacity:0.5'>등록된 Viewer가 없습니다</p>"
                    )

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

        # ── Tab 8: Report ─────────────────────────────────────────────────────
        with gr.Tab("📄 Report", id=8):
            gr.Markdown("## 월간 보고서 / Monthly Report")
            gr.Markdown(
                "선택한 연도·월의 이벤트 데이터를 **Excel(.xlsx)** 파일로 생성합니다.\n\n"
                "- **전체 시트**: 이벤트별 × 날짜별 정탐/오탐\n"
                "- **카메라 시트**: 카메라별 × 날짜별 정탐/오탐\n"
                "- **이벤트별 시트** (9개): 이벤트 × 카메라 × 날짜 정탐/오탐"
            )
            with gr.Row():
                _now_y = datetime.now().year
                _now_m = datetime.now().month
                report_year  = gr.Number(
                    label="연도",
                    value=_now_y,
                    precision=0,
                    minimum=2020,
                    maximum=2099,
                    scale=1,
                )
                report_month = gr.Number(
                    label="월",
                    value=_now_m,
                    precision=0,
                    minimum=1,
                    maximum=12,
                    scale=1,
                )
                btn_report = gr.Button("📄 보고서 생성", variant="primary", scale=2)
            report_status = gr.HTML("")
            report_file   = gr.File(label="", visible=False, interactive=False)

    # ── 이벤트 연결 ───────────────────────────────────────────────────────────

    _today_outs   = [today_out, histogram_out]
    _summary_outs = [bhvr_sum_out, bhvr_line_out, bhvr_detail_out,
                     dst_sum_out,  dst_line_out,  dst_detail_out]

    btn_export_bhvr.click(do_export_bhvr, outputs=[bhvr_export_file])
    btn_export_dst.click(do_export_dst,   outputs=[dst_export_file])
    btn_export_list.click(
        do_export_list,
        inputs=[start_input, end_input, events_check, node_id_input],
        outputs=[list_export_file],
    )

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

    _precision_outs = [
        precision_cards_out, precision_bar_out,
        precision_event_out, precision_node_out,
        precision_trend_out, precision_count_trend_out,
    ]
    btn_precision.click(do_load_precision, inputs=[precision_period], outputs=_precision_outs)
    precision_period.change(do_load_precision, inputs=[precision_period], outputs=_precision_outs)

    _time_all_outs = [
        time_all_cards_out, time_all_heatmap_out,
        time_all_line_out,  time_all_slot_out,
    ]
    btn_time_all.click(do_load_time_dist_all, inputs=[time_all_period], outputs=_time_all_outs)
    time_all_period.change(do_load_time_dist_all, inputs=[time_all_period], outputs=_time_all_outs)

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

    _operator_chart_outs = [operator_chart_out, operator_daily_table_out, operator_monthly_table_out]
    btn_operator.click(do_load_operator_chart, inputs=[operator_select], outputs=_operator_chart_outs)
    operator_select.change(do_load_operator_chart, inputs=[operator_select], outputs=_operator_chart_outs)

    btn_operator_detail.click(do_load_operator_detail, inputs=[operator_detail_select], outputs=[operator_table_out])
    operator_detail_select.change(do_load_operator_detail, inputs=[operator_detail_select], outputs=[operator_table_out])

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

    btn_report.click(
        do_generate_monthly_report,
        inputs=[report_year, report_month],
        outputs=[report_file, report_status],
    )

    app.load(load_today_tab,   outputs=_today_outs)
    app.load(load_summary_tab, outputs=_summary_outs)
    app.load(do_load_operator_init, outputs=[
        operator_select, operator_chart_out, operator_daily_table_out, operator_monthly_table_out,
        operator_detail_select, operator_table_out,
    ])


if __name__ == "__main__":
    print("\n  UI  →  http://localhost:7860\n")
    app.launch(server_name="0.0.0.0", server_port=7860)
