import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from config import ALL_EVENTS

sns.set_theme(style="whitegrid")
plt.rcParams["font.family"]        = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

_CAUSE_COLORS = ["#4C78A8", "#E45756", "#F58518", "#54A24B", "#B279A2",
                 "#9D755D", "#BAB0AC", "#72B7B2"]


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


def _cause_label(c: str) -> str:
    return c if c else "미입력"


def build_time_heatmap(hourly_events: dict, title: str = "시간대 × 이벤트 오탐 히트맵"):
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
    ax.set_title(title, fontsize=14, pad=12)

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


def build_time_line(hour_total: list, title: str = "시간별 오탐 분포 (0~23시)"):
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
    ax.set_title(title, fontsize=14, pad=12)
    ax.legend(fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


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
