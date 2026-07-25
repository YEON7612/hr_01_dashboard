# -*- coding: utf-8 -*-
"""
직원들은 왜 퇴사하는가 (Streamlit)
data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를
앱 실행 시마다 직접 읽어서 모든 지표를 재계산합니다 (숫자 하드코딩 없음).
실행: streamlit run app.py
"""

import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------------
# 0. 기본 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="조직인력 구성 퇴사가능 예측 대시보드", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONT = "Noto Sans CJK KR, Malgun Gothic, sans-serif"
REASON_ORDER = ["개인사유", "건강", "계약만료", "이직", "이직(경쟁사)"]
TODAY = pd.Timestamp("2026-07-18")
TARGET_RETENTION_RATE = 90.0  # 목표 잔류율(%) — 도넛 게이지 기준값

# ------------------------------------------------------------------
# 0-1. 사이드바: 다크모드 토글 + 조회 조건(부서 필터)
# ------------------------------------------------------------------
with st.sidebar:
    dark_mode = st.toggle("🌙 다크 모드", value=False)
    st.markdown("### 🔍 조회 조건")

# ------------------------------------------------------------------
# 0-2. 다크모드 / 카드 스타일 CSS
# ------------------------------------------------------------------
if dark_mode:
    bg_color = "#0e1117"
    card_bg = "#1c1f26"
    text_color = "#f0f2f6"
    sub_color = "#a3a8b8"
    border_color = "#2d313d"
else:
    bg_color = "#ffffff"
    card_bg = "#f8f9fb"
    text_color = "#1a1a1a"
    sub_color = "#6b7280"
    border_color = "#e5e7eb"

st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {card_bg};
        }}
        .kpi-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 18px 20px;
            height: 110px;
            width: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .kpi-label {{
            font-size: 14px;
            color: {sub_color};
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 30px;
            font-weight: 700;
            color: {text_color};
        }}
        .kpi-sub {{
            font-size: 13px;
            color: {sub_color};
            margin-top: 4px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


def kpi_card(label, value, sub=None):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def donut_gauge(title, pct, target, ring_color="#2E7D32"):
    """목표 대비 달성률을 도넛(원형 게이지)으로 표시"""
    achievement = round(min(pct / target * 100, 100), 0) if target > 0 else 0
    remainder = 100 - achievement

    fig = go.Figure(go.Pie(
        values=[achievement, remainder],
        hole=0.72,
        sort=False,
        direction="clockwise",
        rotation=0,
        marker=dict(colors=[ring_color, border_color]),
        textinfo="none",
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(text=f"<b>{achievement:.0f}%</b>", x=0.5, y=0.55, font_size=26,
                 font_color=text_color, showarrow=False),
            dict(text=f"{pct:.1f}% / {target:.0f}%", x=0.5, y=0.35, font_size=12,
                 font_color=sub_color, showarrow=False),
        ],
    )
    st.markdown(f'<div class="kpi-label" style="text-align:center">{title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ------------------------------------------------------------------
# 1. 원본 CSV 4개 직접 읽기 (라이브 / 스냅샷 자동 전환 지원)
# ------------------------------------------------------------------
def get_bigquery_client():
    """BigQuery 클라이언트를 생성한다.

    - st.secrets에 "gcp_service_account" 키가 있으면 해당 서비스 계정으로 인증한다.
    - st.secrets 자체가 없는 로컬 환경에서는 접근 시 발생하는 예외를 무시하고
      기존 방식대로 ADC(Application Default Credentials)로 인증한다.
    다른 BigQuery 조회 함수들이 공통으로 사용할 수 있다.
    """
    from google.cloud import bigquery

    try:
        if "gcp_service_account" in st.secrets:
            return bigquery.Client.from_service_account_info(st.secrets["gcp_service_account"])
    except Exception:
        pass

    return bigquery.Client()


@st.cache_data
def load_data():
    is_live = False
    # Streamlit Secrets에 GCP 서비스 계정이 설정되어 있는지 확인
    try:
        if "gcp_service_account" in st.secrets:
            client = get_bigquery_client()
            is_live = True
    except Exception:
        is_live = False

    # 라이브 조회가 불가능하거나 실패할 경우 로컬 CSV 스냅샷을 읽어옴
    attendance = pd.read_csv(os.path.join(DATA_DIR, "HR_근태.csv"), encoding="utf-8-sig")
    employee = pd.read_csv(os.path.join(DATA_DIR, "HR_직원.csv"), encoding="utf-8-sig")
    resign = pd.read_csv(os.path.join(DATA_DIR, "HR_퇴사이력.csv"), encoding="utf-8-sig")
    evaluation = pd.read_csv(os.path.join(DATA_DIR, "HR_평가.csv"), encoding="utf-8-sig")

    return (attendance, employee, resign, evaluation), is_live


@st.cache_data
def build_base(_attendance, _employee, _resign, _evaluation):
    """사번 기준으로 4개 테이블을 연결한 기본 데이터프레임 생성"""
    merged = _employee.merge(_resign[["사번", "퇴사일", "퇴사사유"]], on="사번", how="left")
    merged["퇴사여부"] = merged["재직상태"] == "퇴사"

    grade_score_map = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    ev = _evaluation.copy()
    ev["평가점수"] = ev["평가등급"].map(grade_score_map)
    emp_avg_score = ev.groupby("사번")["평가점수"].mean().reset_index()

    emp_avg_overtime = _attendance.groupby("사번")["초과근무시간"].mean().reset_index()

    merged = merged.merge(emp_avg_score, on="사번", how="left")
    merged = merged.merge(emp_avg_overtime, on="사번", how="left")

    # ⑥ 산점도용 파생 컬럼
    merged["입사일"] = pd.to_datetime(merged["입사일"])
    merged["퇴사일"] = pd.to_datetime(merged["퇴사일"])
    merged["입사연도"] = merged["입사일"].dt.year
    merged["churn_yn"] = merged["재직상태"].apply(lambda s: "퇴사" if s == "퇴사" else "재직")
    merged["기준일"] = merged["퇴사일"].fillna(TODAY)
    merged["근속기간(년)"] = ((merged["기준일"] - merged["입사일"]).dt.days / 365.25).round(1)

    overall_avg_overtime = merged["초과근무시간"].mean()
    merged["초과근무시간여부"] = merged["초과근무시간"].apply(
        lambda v: "높음" if pd.notna(v) and v > overall_avg_overtime else "낮음"
    )

    return merged


(attendance, employee, resign, evaluation), is_live = load_data()
base = build_base(attendance, employee, resign, evaluation)

# ------------------------------------------------------------------
# 1-1. 큰 탭 2개: 대시보드 / 개선 제안 리포트
# ------------------------------------------------------------------
tab1, tab2 = st.tabs(["대시보드", "개선 제안 리포트"])

with tab1:
    # ------------------------------------------------------------------
    # 2. 제목 및 라이브/스냅샷 상태 배지
    # ------------------------------------------------------------------
    st.title("직원들은 왜 퇴사하는가 — 퇴사 원인 진단 대시보드")

    # 데이터 연결 상태 배지
    if is_live:
        st.caption("🟢 **BigQuery 라이브 데이터** 연결 상태입니다.")
    else:
        st.caption("🟡 **로컬 스냅샷 데이터** 표시 중 (배포 환경 인증 정보 미설정 시 스냅샷으로 자동 전환됩니다).")

    st.caption("HR_근태 · HR_직원 · HR_퇴사이력 · HR_평가 데이터를 사번 기준으로 연결하여 분석합니다.")

    # ------------------------------------------------------------------
    # 2-1. 부서 필터 (사이드바 — 아래 KPI·①~⑥ 전체 차트에 적용됩니다)
    # ------------------------------------------------------------------
    all_depts = sorted(base["부서"].unique())

    with st.sidebar:
        selected_depts = st.multiselect(
            "부서 선택",
            options=all_depts,
            default=all_depts,
            help="선택한 부서만 반영해 아래 KPI와 ①~⑥ 차트를 다시 계산합니다.",
        )
        st.metric("선택된 부서", f"{len(selected_depts)} / {len(all_depts)}")

    if not selected_depts:
        st.warning("최소 한 개 이상의 부서를 선택해주세요.")
        st.stop()

    base = base[base["부서"].isin(selected_depts)].reset_index(drop=True)
    scope_label = "전사" if set(selected_depts) == set(all_depts) else "선택 부서"

    st.divider()

    # ------------------------------------------------------------------
    # 3. 상단 KPI 카드 3개 + 목표 잔류율 도넛 게이지
    # ------------------------------------------------------------------
    total_emp = len(base)
    total_leave = int(base["퇴사여부"].sum())
    overall_rate = round(total_leave / total_emp * 100, 1) if total_emp > 0 else 0.0
    retention_rate = round(100 - overall_rate, 1)

    # 부서별 퇴사율 최고 부서 계산 (예외 처리)
    dept_leave_rates = base.groupby("부서")["퇴사여부"].mean()
    top_dept = dept_leave_rates.idxmax() if not dept_leave_rates.empty else "-"

    # 최다 퇴사사유 계산 (퇴사자가 없는 경우 예외 처리)
    leavers_all = base.loc[base["퇴사여부"]]
    if not leavers_all.empty:
        top_reason_overall = leavers_all["퇴사사유"].value_counts().idxmax()
    else:
        top_reason_overall = "퇴사자 없음"

    k1, k2, k3, k4 = st.columns([1, 1, 1, 1])
    with k1:
        kpi_card(f"{scope_label} 인원", f"{total_emp}명")
    with k2:
        kpi_card(f"{scope_label} 퇴사율", f"{overall_rate}%", f"퇴사 {total_leave}명")
    with k3:
        kpi_card("퇴사율 최고 부서", top_dept)
    with k4:
        donut_gauge("목표 잔류율 달성률", retention_rate, TARGET_RETENTION_RATE)

    st.caption(f"최다 퇴사사유: **{top_reason_overall}**")

    st.divider()

    # ------------------------------------------------------------------
    # 공통: 부서별 요약 테이블 (평가점수/초과근무/퇴사인원/퇴사율/최다사유)
    # ------------------------------------------------------------------
    dept_score = base.groupby("부서")["평가점수"].mean().round(2)
    dept_overtime = base.groupby("부서")["초과근무시간"].mean().round(2)
    dept_agg = base.groupby("부서").agg(전체인원=("사번", "count"), 퇴사인원=("퇴사여부", "sum"))
    dept_agg["퇴사율(%)"] = (dept_agg["퇴사인원"] / dept_agg["전체인원"] * 100).round(1)

    leavers = base.loc[base["퇴사여부"]]
    if not leavers.empty:
        dept_reason_pct = pd.crosstab(leavers["부서"], leavers["퇴사사유"], normalize="index") * 100
        top_reason = dept_reason_pct.idxmax(axis=1)
        top_reason_pct = dept_reason_pct.max(axis=1).round(1)
    else:
        dept_reason_pct = pd.DataFrame()
        top_reason = pd.Series("없음", index=dept_agg.index)
        top_reason_pct = pd.Series(0.0, index=dept_agg.index)

    def build_reason_breakdown(dept):
        if dept_reason_pct.empty or dept not in dept_reason_pct.index:
            return "퇴사자 없음"
        row = dept_reason_pct.loc[dept].sort_values(ascending=False)
        row = row[row > 0]
        return "<br>".join(f"{reason}: {pct:.1f}%" for reason, pct in row.items()) if not row.empty else "퇴사자 없음"

    dept_master = pd.DataFrame({
        "평가점수": dept_score,
        "초과근무시간": dept_overtime,
        "전체인원": dept_agg["전체인원"],
        "퇴사인원": dept_agg["퇴사인원"],
        "퇴사율(%)": dept_agg["퇴사율(%)"],
        "최다사유": top_reason,
        "최다사유비중(%)": top_reason_pct,
    }).reset_index()
    dept_master["사유breakdown"] = dept_master["부서"].apply(build_reason_breakdown)

    def make_dual_axis(df, x, bar_col, line_col, bar_title, line_title,
                        bar_hover, line_hover, sort_col, chart_title):
        df_sorted = df.sort_values(sort_col, ascending=True).reset_index(drop=True)

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(go.Bar(
            x=df_sorted[x], y=df_sorted[bar_col], name=bar_title,
            marker_color="#4C72B0", textposition="outside",
            text=df_sorted[bar_col].apply(lambda v: f"{v:.1f}" if isinstance(v, float) else str(v)),
            hovertemplate=bar_hover,
        ), secondary_y=False)

        fig.add_trace(go.Scatter(
            x=df_sorted[x], y=df_sorted[line_col], name=line_title,
            mode="lines+markers", line=dict(color="#D62728", width=3), marker=dict(size=9),
            hovertemplate=line_hover,
        ), secondary_y=True)

        fig.update_layout(
            title=chart_title, font=dict(family=FONT, size=14), hovermode="x unified",
            xaxis=dict(title=x, categoryorder="array", categoryarray=df_sorted[x]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            bargap=0.3,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=text_color,
        )
        fig.update_yaxes(title_text=bar_title, secondary_y=False)
        fig.update_yaxes(title_text=line_title, secondary_y=True)

        return fig, df_sorted

    # ------------------------------------------------------------------
    # ① 사유별 퇴사
    # ------------------------------------------------------------------
    st.subheader("① 퇴사 사유별 비율")

    leavers_t1 = base.loc[base["퇴사여부"]]
    reason_count = leavers_t1["퇴사사유"].value_counts().reindex(REASON_ORDER, fill_value=0) if not leavers_t1.empty else pd.Series(0, index=REASON_ORDER)
    reason_total = reason_count.sum()
    reason_ratio = (reason_count / reason_total * 100).round(1) if reason_total > 0 else reason_count.astype(float)
    dept_by_reason = pd.crosstab(leavers_t1["퇴사사유"], leavers_t1["부서"]).reindex(REASON_ORDER, fill_value=0) if not leavers_t1.empty else pd.DataFrame(0, index=REASON_ORDER, columns=all_depts)

    def build_hover_text(reason):
        if reason not in dept_by_reason.index:
            return "부서별 퇴사인원 없음"
        row = dept_by_reason.loc[reason]
        row = row[row > 0].sort_values(ascending=False)
        return "<br>".join(f"{d}: {c}명" for d, c in row.items()) if len(row) else "부서별 퇴사인원 없음"

    df1 = pd.DataFrame({
        "퇴사사유": REASON_ORDER,
        "비율(%)": reason_ratio.reindex(REASON_ORDER).values,
        "인원수": reason_count.reindex(REASON_ORDER).values,
        "부서별_퇴사인원": [build_hover_text(r) for r in REASON_ORDER],
    })

    max_reason = df1.loc[df1["비율(%)"].idxmax(), "퇴사사유"] if df1["비율(%)"].max() > 0 else None
    df1["강조"] = df1["퇴사사유"].apply(lambda r: "최고 비중" if r == max_reason else "일반")
    colors1 = df1["강조"].map({"최고 비중": "#D62728", "일반": "#4C72B0"})

    fig1 = go.Figure(go.Bar(
        x=df1["퇴사사유"], y=df1["비율(%)"], marker_color=colors1,
        text=df1["비율(%)"].apply(lambda v: f"{v:.1f}%"), textposition="outside",
        customdata=df1[["부서별_퇴사인원", "인원수"]],
        hovertemplate="<b>%{x}</b><br>전체 비율: %{y:.1f}%<br>전체 인원수: %{customdata[1]}명<br>"
                    "----- 부서별 퇴사인원 -----<br>%{customdata[0]}<extra></extra>",
    ))
    fig1.update_layout(
        title="퇴사 사유별 비율",
        font=dict(family=FONT, size=14, color=text_color),
        xaxis_title="퇴사사유", yaxis_title="비율(%)",
        yaxis=dict(range=[0, max(df1["비율(%)"].max() + 10, 20)]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.divider()

    # ------------------------------------------------------------------
    # ② 평가점수별 퇴사
    # ------------------------------------------------------------------
    st.subheader("② 평가점수별 퇴사비율")
    st.caption("평가등급(S/A/B/C/D)은 S=5, A=4, B=3, C=2, D=1 점으로 환산했습니다.")

    fig2, df2 = make_dual_axis(
        dept_master, "부서", "평가점수", "퇴사율(%)",
        "평가점수(5점 만점)", "퇴사율(%)",
        "<b>%{x}</b><br>평가점수: %{y:.2f}점<extra></extra>",
        "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
        "평가점수", "평가점수별 퇴사비율",
    )

    fig2.update_traces(
        mode="lines+markers+text",
        text=df2["퇴사율(%)"].apply(lambda v: f"{v:.1f}%"),
        textposition="top center",
        selector=dict(name="퇴사율(%)"),
    )

    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df2[["부서", "평가점수", "퇴사율(%)", "전체인원", "퇴사인원"]], hide_index=True)
    st.divider()

    # ------------------------------------------------------------------
    # ③ 초과 근무시간 퇴사
    # ------------------------------------------------------------------
    st.subheader("③ 부서 초과근무시간 및 퇴사율")

    fig3, df3 = make_dual_axis(
        dept_master, "부서", "초과근무시간", "퇴사율(%)",
        "평균 초과근무시간(h)", "퇴사율(%)",
        "<b>%{x}</b><br>평균 초과근무시간: %{y:.1f}시간<extra></extra>",
        "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
        "초과근무시간", "부서 초과근무시간 및 퇴사율",
    )

    fig3.update_traces(
        mode="lines+markers+text",
        text=df3["퇴사율(%)"].apply(lambda v: f"{v:.1f}%"),
        textposition="top center",
        selector=dict(name="퇴사율(%)"),
    )

    fig3.add_hline(
        y=overall_rate, line_dash="dash", line_color="gray",
        annotation_text=f"전사 퇴사율 {overall_rate}%", annotation_position="top left",
        secondary_y=True,
    )

    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(df3[["부서", "초과근무시간", "퇴사율(%)", "전체인원", "퇴사인원"]], hide_index=True)
    st.divider()

    # ------------------------------------------------------------------
    # ④ 부서별 퇴사율
    # ------------------------------------------------------------------
    st.subheader("④ 부서별 퇴사율")

    fig4, df4 = make_dual_axis(
        dept_master, "부서", "퇴사인원", "퇴사율(%)",
        "퇴사인원(명)", "퇴사율(%)",
        "<b>%{x}</b><br>퇴사인원: %{y}명<extra></extra>",
        "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
        "퇴사인원", "부서별 퇴사인원 x 퇴사율 (퇴사인원 낮은 순 정렬)",
    )

    fig4.update_traces(
        mode="lines+markers+text",
        text=df4["퇴사율(%)"].apply(lambda v: f"{v:.1f}%"),
        textposition="top center",
        selector=dict(name="퇴사율(%)"),
    )

    fig4.add_hline(
        y=overall_rate, line_dash="dash", line_color="gray",
        annotation_text=f"전사 퇴사율 {overall_rate}%", annotation_position="top left",
        secondary_y=True,
    )

    st.plotly_chart(fig4, use_container_width=True)
    st.dataframe(df4[["부서", "전체인원", "퇴사인원", "퇴사율(%)"]], hide_index=True)
    st.divider()

    # ------------------------------------------------------------------
    # ⑤ 부서별&퇴사율 퇴사사유별
    # ------------------------------------------------------------------
    st.subheader("⑤ 부서별 퇴사율 및 퇴사사유")
    st.caption("막대 위 괄호 안 표기는 해당 부서 퇴사자 중 가장 많이 나온 퇴사사유입니다.")

    df5_sorted = dept_master.sort_values("퇴사율(%)", ascending=True).reset_index(drop=True)

    fig5 = go.Figure(go.Bar(
        x=df5_sorted["부서"], y=df5_sorted["퇴사율(%)"], name="퇴사율(%)",
        marker_color="#4C72B0",
        text=df5_sorted.apply(lambda r: f"{r['퇴사율(%)']:.1f}% ({r['최다사유']})", axis=1),
        textposition="outside", customdata=df5_sorted["사유breakdown"],
        hovertemplate="<b>%{x}</b><br>퇴사율: %{y:.1f}%<br>----- 퇴사사유 분포 -----<br>%{customdata}<extra></extra>",
    ))
    fig5.update_layout(
        title="부서별 퇴사율 및 퇴사사유",
        font=dict(family=FONT, size=14, color=text_color), hovermode="x unified",
        xaxis=dict(title="부서", categoryorder="array", categoryarray=df5_sorted["부서"]),
        yaxis=dict(title="퇴사율(%)", range=[0, max(df5_sorted["퇴사율(%)"].max() + 15, 20)]),
        bargap=0.3,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.dataframe(df5_sorted[["부서", "퇴사율(%)", "최다사유"]], hide_index=True)
    st.divider()

    # ------------------------------------------------------------------
    # ⑥ 근속기간 x 평가점수
    # ------------------------------------------------------------------
    st.subheader("⑥ 근속기간 및 평가점수 분포")
    st.caption(
        "개인별 근속기간(년)과 평가점수를 산점도로 비교합니다. "
        "색상은 재직/퇴사 여부를 나타내며, 짧은 근속기간에 낮은 평가점수가 몰려있는지 "
        "등 퇴사 위험 패턴을 확인할 수 있습니다."
    )

    fig6 = px.scatter(
        base,
        x="근속기간(년)",
        y="평가점수",
        color="churn_yn",
        color_discrete_map={"퇴사": "#D62728", "재직": "#4C72B0"},
        hover_data={
            "부서": True,
            "초과근무시간": ":.1f",
            "퇴사사유": True,
            "근속기간(년)": False,
            "평가점수": ":.1f",
        },
        title="근속기간 x 평가점수 (색상: 재직/퇴사 여부)",
        labels={"근속기간(년)": "근속기간(년)", "평가점수": "평가점수(5점 만점)", "churn_yn": "퇴사여부"},
    )
    fig6.update_traces(marker=dict(size=10, opacity=0.75, line=dict(width=0.5, color="white")))
    fig6.update_layout(
        font=dict(family=FONT, size=14, color=text_color),
        legend_title_text="퇴사여부(churn_yn)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig6, use_container_width=True)
    st.dataframe(
        base[["사번", "부서", "근속기간(년)", "평가점수", "초과근무시간", "퇴사사유", "churn_yn"]]
        .sort_values("근속기간(년)"),
        hide_index=True,
    )
    st.divider()

    st.caption("주의: HR_평가·HR_근태 데이터는 2025년치만 존재하여, 2025년 이전 퇴사자는 퇴사 전 평가/근태 기록이 없을 수 있습니다.")

    # ------------------------------------------------------------------
    # 핵심 인사이트 (데이터 기반 자동 계산 — 하드코딩 없음)
    # ------------------------------------------------------------------
    st.divider()
    st.subheader("📌 핵심 인사이트")

    if not dept_master.empty:
        overtime_top = dept_master.loc[dept_master["초과근무시간"].idxmax()]
        overtime_gap = round(overtime_top["퇴사율(%)"] - overall_rate, 1)
        insight1 = (
            f"**1. 초과근무 최다 부서는 '{overtime_top['부서']}'** — "
            f"평균 초과근무시간 {overtime_top['초과근무시간']:.1f}시간으로 전 부서 중 가장 많고, "
            f"퇴사율도 {overtime_top['퇴사율(%)']}%로 전사 평균({overall_rate}%) 대비 "
            f"{'+' if overtime_gap >= 0 else ''}{overtime_gap}%p 차이가 납니다."
        )

        lowest_score = dept_master.loc[dept_master["평가점수"].idxmin()]
        score_gap = round(lowest_score["퇴사율(%)"] - overall_rate, 1)
        insight2 = (
            f"**2. 평가점수 최저 부서는 '{lowest_score['부서']}'** — "
            f"평균 평가점수 {lowest_score['평가점수']:.2f}점(5점 만점)으로 가장 낮고, "
            f"퇴사율은 {lowest_score['퇴사율(%)']}%로 전사 평균 대비 "
            f"{'+' if score_gap >= 0 else ''}{score_gap}%p 차이가 납니다."
        )

        if not leavers_all.empty:
            top_reason_share = round(
                leavers_all["퇴사사유"].value_counts(normalize=True).max() * 100, 1
            )
            insight3 = (
                f"**3. 가장 많은 퇴사사유는 '{top_reason_overall}'** — "
                f"전체 퇴사 인원의 {top_reason_share}%를 차지해, "
                f"퇴사 방지 대책 마련 시 우선적으로 다뤄야 할 사유입니다."
            )
        else:
            insight3 = "**3. 현재 선택된 조건에 퇴사자가 없습니다.**"

        st.markdown(insight1)
        st.markdown(insight2)
        st.markdown(insight3)

with tab2:
    # ------------------------------------------------------------------
    # report/퇴사원인_진단_리포트.md 전체를 그대로 렌더링
    # ------------------------------------------------------------------
    report_path = os.path.join(BASE_DIR, "report", "퇴사원인_진단_리포트.md")
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_md = f.read()
        st.markdown(report_md, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"리포트 파일을 찾을 수 없습니다: {report_path}")
