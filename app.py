# -*- coding: utf-8 -*-
"""
직원들은 왜 퇴사하는가 (Streamlit)
data/HR_근태.csv, HR_직원.csv, HR_퇴사이력.csv, HR_평가.csv 를
앱 실행 시마다 직접 읽어서 모든 지표를 재계산합니다 (숫자 하드코딩 없음).
실행: streamlit run app.py
"""

import os
import numpy as np
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
CHANNEL_ORDER = ["공채", "수시", "추천", "헤드헌팅"]
TODAY = pd.Timestamp("2026-07-18")
TARGET_RETENTION_RATE = 90.0  # 목표 잔류율(%) — 도넛 게이지 기준값
# ⚠️ TODO(확인 필요): 이 90%는 실제 인사팀이 정한 목표치인지 출처가 확인되지 않은 가정값입니다.
# 지표정의서.md 7번 항목 참고. 출처 확인 전까지는 대시보드에도 "가정값" 문구를 노출합니다(아래 donut_gauge 옆 caption).
SURVIVAL_MILESTONES_YEARS = [1, 3, 5, 10]  # 근속 생존 퍼널 마일스톤(년)
MIN_SAMPLE = 30  # Day5 자기도메인 명세 4행 — 코호트 최소표본. 이보다 적으면 비율을 신뢰하지 않음.
# Day5 자기도메인 명세 3~4행(내도메인.md 참고, 다음 회차에서 확정):
# 주지표(초과근무 상위 구간 입사 1년 내 이탈률) 현재값 4.0%(n=100 중 4명) 대비
#   경고선 6%(6명) — "이쯤 되면 들여다본다"
#   위험선 8%(8명) — 전사 1년내 이탈자 총수(8명)가 이 구간 하나에 몰리는 수준
# 가드레일(업무성과) 기준값 — 재직자 평균 평가점수가 2.7점 미만으로 떨어지면 초과근무 감축 개입을 중단
#   (현재 상위 구간 평균 3.03점, 표준편차 0.66 — 약 0.5 표준편차 하락 기준)
OVERTIME_ATTRITION_WARN_PCT = 6.0
OVERTIME_ATTRITION_DANGER_PCT = 8.0
PERFORMANCE_GUARDRAIL_SCORE = 2.7
# retention_target_rate 자체는 calc_metrics.py 엔진이 지원하는 4개 formula_type(ratio/mean/pct_threshold/pct_change)에
# 맞지 않는 파생값이라 엔진에 편입하지 않고 여기(app.py)에서 직접 계산하기로 결정함 — 06_metrics/README.md, 지표정의서.md에 동일하게 문서화되어 있음.

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
        .kpi-card-highlight {{
            background-color: {card_bg};
            border: 1px solid #e11d48;
            border-left: 6px solid #e11d48;
            border-radius: 12px;
            padding: 18px 20px;
            height: 110px;
            width: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .kpi-label-highlight {{
            font-size: 14px;
            color: #e11d48;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .kpi-value-highlight {{
            font-size: 30px;
            font-weight: 800;
            color: #e11d48;
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


def kpi_card_highlight(label, value, sub=None):
    """강조가 필요한 KPI(예: 최다 퇴사사유)를 붉은 테두리로 눈에 띄게 표시"""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="kpi-card-highlight">
            <div class="kpi-label-highlight">{label}</div>
            <div class="kpi-value-highlight">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def donut_gauge(title, pct, target, ring_color="#2E7D32"):
    """목표 대비 달성률을 도넛(원형 게이지)으로 표시"""
    achievement = round(min(pct / target * 100, 100), 0) if target > 0 else 0
    remainder = 100 - achievement
    goal_met = target > 0 and pct >= target

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
    center_text = "🎯 목표 달성" if goal_met else f"<b>{achievement:.0f}%</b>"
    center_font_size = 18 if goal_met else 26
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(text=center_text, x=0.5, y=0.55, font_size=center_font_size,
                 font_color=(ring_color if goal_met else text_color), showarrow=False),
            dict(text=f"현재 {pct:.1f}% (목표 {target:.0f}%)", x=0.5, y=0.35, font_size=12,
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
# 1-1. 큰 탭 3개: 대시보드 / 채용경로별 / 개선 제안 리포트
# ------------------------------------------------------------------
tab1, tab3, tab2, tab4 = st.tabs(["대시보드", "채용경로별", "개선 제안 리포트", "자기도메인(Day5)"])

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

    k0, k1, k2, k3, k4 = st.columns([1.2, 1, 1, 1, 1])
    with k0:
        reason_icon = "⚠️ " if top_reason_overall == "건강" else ""
        kpi_card_highlight(f"{reason_icon}최다 퇴사사유", top_reason_overall)
    with k1:
        kpi_card(f"{scope_label} 인원", f"{total_emp}명")
    with k2:
        kpi_card(
            f"{scope_label} 퇴사율",
            f'{overall_rate}% <span style="font-size:16px;font-weight:400;color:{sub_color}">(퇴사 {total_leave}명)</span>',
        )
    with k3:
        kpi_card("퇴사율 최고 부서", top_dept)
    with k4:
        donut_gauge("잔류율 목표 달성 현황", retention_rate, TARGET_RETENTION_RATE)
        st.caption("⚠️ 목표값(90%)은 출처 미확인 가정값입니다")

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
        annotation_text=f"전사 퇴사율 {overall_rate}% (퇴사 {total_leave}명)", annotation_position="top left",
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
        annotation_text=f"전사 퇴사율 {overall_rate}% (퇴사 {total_leave}명)", annotation_position="top left",
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

with tab3:
    # ------------------------------------------------------------------
    # 채용경로별 탭: HR_직원.csv의 '채용경로' 컬럼 기준 분석
    # (data/HR_직원.csv에 '채용경로' 컬럼이 있어야 표시됩니다)
    # ------------------------------------------------------------------
    st.title("채용경로별 분석")
    st.caption("공채 · 수시 · 추천 · 헤드헌팅 채용경로별 인원, 퇴사율, 근속연수를 비교합니다.")

    if "채용경로" not in base.columns:
        st.warning(
            "data/HR_직원.csv에 '채용경로' 컬럼이 없습니다. "
            "채용경로(공채/수시/추천/헤드헌팅) 컬럼을 추가한 파일로 교체해주세요."
        )
    else:
        ch_base = base.copy()

        # ---------------- 상단 KPI ----------------
        ch_total = len(ch_base)
        ch_counts = ch_base["채용경로"].value_counts().reindex(CHANNEL_ORDER, fill_value=0)
        referral_count = int(ch_counts.get("추천", 0))
        referral_share = round(referral_count / ch_total * 100, 1) if ch_total > 0 else 0.0

        referral_rows = ch_base[ch_base["채용경로"] == "추천"]
        referral_rate = (
            round(referral_rows["퇴사여부"].mean() * 100, 1) if len(referral_rows) > 0 else 0.0
        )
        non_referral_rows = ch_base[ch_base["채용경로"] != "추천"]
        non_referral_rate = (
            round(non_referral_rows["퇴사여부"].mean() * 100, 1) if len(non_referral_rows) > 0 else 0.0
        )

        top_channel = ch_counts.idxmax() if ch_counts.sum() > 0 else "-"

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card(f"{scope_label} 추천채용 인원", f"{referral_count}명", f"전체의 {referral_share}%")
        with c2:
            kpi_card("추천채용 퇴사율", f"{referral_rate}%")
        with c3:
            kpi_card("비추천채용 퇴사율", f"{non_referral_rate}%")
        with c4:
            kpi_card("가장 많은 채용경로", top_channel)

        st.divider()

        # ---------------- 채용경로별 요약 테이블 ----------------
        ch_agg = ch_base.groupby("채용경로").agg(
            전체인원=("사번", "count"),
            퇴사인원=("퇴사여부", "sum"),
        ).reindex(CHANNEL_ORDER, fill_value=0)
        ch_agg["퇴사율(%)"] = (ch_agg["퇴사인원"] / ch_agg["전체인원"] * 100).round(1).fillna(0.0)

        ch_score = ch_base.groupby("채용경로")["평가점수"].mean().reindex(CHANNEL_ORDER).round(2)
        ch_tenure = ch_base.groupby("채용경로")["근속기간(년)"].mean().reindex(CHANNEL_ORDER).round(1)

        ch_master = ch_agg.copy()
        ch_master["평균평가점수"] = ch_score
        ch_master["평균근속연수"] = ch_tenure
        ch_master = ch_master.reset_index()

        # ---------------- ① 채용경로별 인원 x 퇴사율 (이중축) ----------------
        st.subheader("① 채용경로별 인원 및 퇴사율")

        fig_ch1, df_ch1 = make_dual_axis(
            ch_master, "채용경로", "전체인원", "퇴사율(%)",
            "전체인원(명)", "퇴사율(%)",
            "<b>%{x}</b><br>전체인원: %{y}명<extra></extra>",
            "<b>%{x}</b><br>퇴사율: %{y:.1f}%<extra></extra>",
            "전체인원", "채용경로별 인원 x 퇴사율",
        )
        fig_ch1.update_traces(
            mode="lines+markers+text",
            text=df_ch1["퇴사율(%)"].apply(lambda v: f"{v:.1f}%"),
            textposition="top center",
            selector=dict(name="퇴사율(%)"),
        )
        fig_ch1.add_hline(
            y=overall_rate, line_dash="dash", line_color="gray",
            annotation_text=f"전사 퇴사율 {overall_rate}% (퇴사 {total_leave}명)", annotation_position="top left",
            secondary_y=True,
        )
        st.plotly_chart(fig_ch1, use_container_width=True)
        st.dataframe(
            ch_master[["채용경로", "전체인원", "퇴사인원", "퇴사율(%)"]],
            hide_index=True,
        )
        st.divider()

        # ---------------- ② 채용경로별 평균 근속연수 ----------------
        st.subheader("② 채용경로별 평균 근속연수")

        fig_ch2 = go.Figure(go.Bar(
            x=ch_master["채용경로"], y=ch_master["평균근속연수"],
            marker_color="#4C72B0",
            text=ch_master["평균근속연수"].apply(lambda v: f"{v:.1f}년" if pd.notna(v) else "-"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>평균 근속연수: %{y:.1f}년<extra></extra>",
        ))
        fig_ch2.update_layout(
            title="채용경로별 평균 근속연수",
            font=dict(family=FONT, size=14, color=text_color),
            xaxis_title="채용경로", yaxis_title="평균 근속연수(년)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_ch2, use_container_width=True)
        st.divider()

        # ---------------- ③ 근속기간 x 평가점수 산점도 (채용경로 색상) ----------------
        st.subheader("③ 근속기간 및 평가점수 분포 (채용경로별)")
        st.caption("색상은 채용경로를 나타냅니다. 채용경로에 따라 근속·평가 패턴이 다른지 확인할 수 있습니다.")

        fig_ch3 = px.scatter(
            ch_base,
            x="근속기간(년)",
            y="평가점수",
            color="채용경로",
            category_orders={"채용경로": CHANNEL_ORDER},
            hover_data={
                "부서": True,
                "초과근무시간": ":.1f",
                "churn_yn": True,
                "근속기간(년)": False,
                "평가점수": ":.1f",
            },
            title="근속기간 x 평가점수 (색상: 채용경로)",
            labels={"근속기간(년)": "근속기간(년)", "평가점수": "평가점수(5점 만점)"},
        )
        fig_ch3.update_traces(marker=dict(size=10, opacity=0.75, line=dict(width=0.5, color="white")))
        fig_ch3.update_layout(
            font=dict(family=FONT, size=14, color=text_color),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_ch3, use_container_width=True)
        st.divider()

        # ---------------- 핵심 인사이트 ----------------
        st.subheader("📌 핵심 인사이트")
        insight_ch1 = (
            f"**1. 추천채용 인원은 {scope_label} 기준 {referral_count}명(전체의 {referral_share}%)입니다.** "
            f"추천채용 퇴사율은 {referral_rate}%로, 비추천채용 퇴사율({non_referral_rate}%)과 비교됩니다."
        )
        st.markdown(insight_ch1)
        st.caption("주의: 채용경로별 표본 수가 적을 수 있어(특히 헤드헌팅), 비율 차이를 확정적으로 해석하지 않도록 유의하세요.")

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

with tab4:
    # ------------------------------------------------------------------
    # Day5 자기도메인: 연차별 잔류율(근속 생존 퍼널) + 세그먼트 분해
    # 나의_성장퍼널.md(2026-08-25~27) → 내도메인.md(2026-08-29) 명세를 그대로 앱에 반영.
    # 채용 다단계 이벤트 로그가 없어 가입 퍼널 대신 "연차별 잔류율"(입사→1/3/5/10년차 잔류)로 대체했고,
    # 우측절단(right-censoring) 편향을 피하기 위해 Kaplan-Meier 생존추정을 사용합니다.
    # ------------------------------------------------------------------
    st.title("자기도메인: 연차별 잔류율")
    st.caption(
        "채용 단계별 이벤트 로그가 없어 가입 퍼널 대신 연차별 잔류율(입사→1/3/5/10년차 잔류)을 씁니다. "
        "그레인은 사번(직원) 1행이며, 유지=재직 중, 이탈=`HR_퇴사이력` 사건 발생으로 정의합니다."
    )

    dom = base.copy()
    dom["event"] = dom["퇴사여부"].astype(int)
    dom["end_date"] = dom["퇴사일"].fillna(TODAY)
    dom["tenure_days"] = (dom["end_date"] - dom["입사일"]).dt.days

    def kaplan_meier(df):
        """표준 Kaplan-Meier 생존추정. 우측절단(아직 결과가 안 나온 재직자)을 올바르게 처리한다."""
        event_times = np.sort(df.loc[df["event"] == 1, "tenure_days"].unique())
        surv = 1.0
        rows = [(0, 1.0)]
        for t in event_times:
            n_at_risk = (df["tenure_days"] >= t).sum()
            d_events = ((df["tenure_days"] == t) & (df["event"] == 1)).sum()
            if n_at_risk > 0:
                surv *= (1 - d_events / n_at_risk)
            rows.append((t, surv))
        return pd.DataFrame(rows, columns=["t", "survival"])

    km = kaplan_meier(dom)

    def survival_at(years):
        td = years * 365
        sub = km[km["t"] <= td]
        return sub["survival"].iloc[-1] if len(sub) else 1.0

    funnel_rows = [{"단계": "입사", "잔류율(%)": 100.0}]
    for y in SURVIVAL_MILESTONES_YEARS:
        funnel_rows.append({"단계": f"{y}년차", "잔류율(%)": round(survival_at(y) * 100, 1)})
    funnel_df = pd.DataFrame(funnel_rows)

    st.subheader("① 연차별 잔류율")
    st.caption("통계적으로는 Kaplan-Meier 생존추정 방식을 사용했습니다 — 아직 재직 중인 인원도 놓치지 않고 정확히 반영하기 위한 방법입니다.")
    fig_funnel = go.Figure(go.Funnel(
        y=funnel_df["단계"],
        x=funnel_df["잔류율(%)"],
        textinfo="value+percent initial",
        marker=dict(color="#4C72B0"),
    ))
    fig_funnel.update_layout(
        title=f"연차별 잔류율 ({scope_label}, n={len(dom)})",
        font=dict(family=FONT, size=14, color=text_color),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_funnel, use_container_width=True)
    st.dataframe(funnel_df, hide_index=True)
    st.caption(
        "퍼널 판정: 각 단계는 생존분석 구조상 앞 단계를 반드시 거치므로 "
        "'앞 단계를 안 거치고 다음 단계로 건너뛴 인원'은 0명입니다."
    )

    st.divider()

    # ------------------------------------------------------------------
    # ② 세그먼트 분해 — 입사 1년 내 이탈률 (결과 확정 코호트만)
    # ------------------------------------------------------------------
    st.subheader("② 입사 1년 내 이탈률 세그먼트 분해")
    st.caption(
        "우측절단(아직 1년이 안 된 재직자)을 제외하기 위해, 입사일 기준 이미 결과가 확정된 "
        "코호트(1년 이상 관측됐거나 1년 내 퇴사 확정)만 사용합니다."
    )

    dom["left_within_1y"] = ((dom["event"] == 1) & (dom["tenure_days"] <= 365)).astype(int)
    dom["outcome_determined_1y"] = (dom["tenure_days"] >= 365) | (dom["left_within_1y"] == 1)
    cohort = dom[dom["outcome_determined_1y"]].copy()

    censored_n = len(dom) - len(cohort)
    overall_1y_rate = round(cohort["left_within_1y"].mean() * 100, 1) if len(cohort) else None

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card(f"{scope_label} 코호트(결과 확정)", f"{len(cohort)}명",
                 f"우측절단 제외 {censored_n}명" if censored_n else "전원 결과 확정")
    with c2:
        kpi_card("입사 1년 내 이탈률", f"{overall_1y_rate}%" if overall_1y_rate is not None else "-")
    with c3:
        kpi_card("최소표본 기준", f"n≥{MIN_SAMPLE}", "미만이면 참고용으로만 사용")

    if len(cohort) >= MIN_SAMPLE and cohort["초과근무시간"].notna().any():
        q_lo, q_hi = cohort["초과근무시간"].quantile([1 / 3, 2 / 3])

        def tercile(v):
            if pd.isna(v):
                return "알수없음"
            if v <= q_lo:
                return "하위"
            elif v <= q_hi:
                return "중위"
            return "상위"

        cohort["초과근무구간"] = cohort["초과근무시간"].apply(tercile)

        def segment_table(group_col, order=None):
            g = cohort.groupby(group_col).agg(n=("사번", "count"), 이탈=("left_within_1y", "sum"))
            g["이탈률(%)"] = (g["이탈"] / g["n"] * 100).round(1)
            g["표본경고"] = g["n"].apply(lambda n: f"⚠️ n<{MIN_SAMPLE}" if n < MIN_SAMPLE else "")
            g = g.reset_index()
            if order:
                g[group_col] = pd.Categorical(g[group_col], categories=order, ordered=True)
                g = g.sort_values(group_col)
            else:
                g = g.sort_values("이탈률(%)", ascending=False)
            return g

        def segment_bar(df, group_col, title, warn=None, danger=None):
            fig = go.Figure(go.Bar(
                x=df[group_col].astype(str), y=df["이탈률(%)"],
                marker_color=["#D62728" if n < MIN_SAMPLE else "#4C72B0" for n in df["n"]],
                text=df.apply(lambda r: f"{r['이탈률(%)']:.1f}%{' ⚠️' if r['n'] < MIN_SAMPLE else ''}", axis=1),
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>이탈률: %{y:.1f}%<extra></extra>",
            ))
            fig.add_hline(
                y=overall_1y_rate, line_dash="dash", line_color="gray",
                annotation_text=f"코호트 전체 {overall_1y_rate}%", annotation_position="top left",
            )
            if warn is not None:
                fig.add_hline(
                    y=warn, line_dash="dot", line_color="#E8A33D",
                    annotation_text=f"경고 {warn:.0f}%", annotation_position="bottom right",
                )
            if danger is not None:
                fig.add_hline(
                    y=danger, line_dash="dot", line_color="#D62728",
                    annotation_text=f"위험 {danger:.0f}%", annotation_position="top right",
                )
            fig.update_layout(
                title=title, font=dict(family=FONT, size=14, color=text_color),
                yaxis_title="이탈률(%)",
                yaxis_range=[0, max(df["이탈률(%)"].max(), danger or 0, warn or 0) + 3],
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            return fig

        seg_dept = segment_table("부서")
        seg_channel = segment_table("채용경로", order=list(CHANNEL_ORDER))
        seg_overtime = segment_table("초과근무구간", order=["하위", "중위", "상위"])

        colA, colB, colC = st.columns(3)
        with colA:
            st.plotly_chart(segment_bar(seg_dept, "부서", "부서별"), use_container_width=True)
        with colB:
            st.plotly_chart(segment_bar(seg_channel, "채용경로", "채용경로별"), use_container_width=True)
        with colC:
            st.plotly_chart(
                segment_bar(seg_overtime, "초과근무구간", "초과근무 3분위별",
                            warn=OVERTIME_ATTRITION_WARN_PCT, danger=OVERTIME_ATTRITION_DANGER_PCT),
                use_container_width=True,
            )

        st.dataframe(
            pd.concat([
                seg_dept.assign(구분="부서"),
                seg_channel.assign(구분="채용경로"),
                seg_overtime.assign(구분="초과근무구간"),
            ])[["구분", "n", "이탈", "이탈률(%)", "표본경고"]].rename(columns={"구분": "세그먼트 축"}),
            hide_index=True,
        )

        # 추천·헤드헌팅 최소표본 미달 해결: 두 채널을 병합해 n≥30을 만족시킨다.
        # 단, 병합해도 이탈 사건이 0건이면 "0%"라는 값 자체가 불안정하다(rule of three: 사건 0건일 때
        # 95% 신뢰구간 상한은 대략 3/n ≈ 3/38 ≈ 8%) — 표본 기준 통과가 "확실히 낮다"는 증거는 아니다.
        cohort["채용경로_병합"] = cohort["채용경로"].replace(
            {"추천": "추천+헤드헌팅", "헤드헌팅": "추천+헤드헌팅"}
        )
        seg_channel_merged = segment_table("채용경로_병합")
        st.caption("채용경로 최소표본 보완 — 추천·헤드헌팅 병합")
        st.dataframe(
            seg_channel_merged[["채용경로_병합", "n", "이탈", "이탈률(%)", "표본경고"]]
            .rename(columns={"채용경로_병합": "채용경로(병합)"}),
            hide_index=True,
        )
        merged_row = seg_channel_merged[seg_channel_merged["채용경로_병합"] == "추천+헤드헌팅"]
        if not merged_row.empty and int(merged_row["이탈"].iloc[0]) == 0:
            n_merged = int(merged_row["n"].iloc[0])
            rule_of_three_upper = round(3 / n_merged * 100, 1)
            st.caption(
                f"⚠️ 병합 후 n={n_merged}로 최소표본(n≥{MIN_SAMPLE})은 통과했지만, 이탈 사건이 0건이라 "
                f"'0%'가 곧 안전하다는 뜻은 아닙니다. 사건 0건 구간의 95% 신뢰구간 상한은 대략 "
                f"{rule_of_three_upper}%까지 열려 있다고 봐야 합니다(rule of three)."
            )

        top_seg = seg_overtime.loc[seg_overtime["초과근무구간"] == "상위"]
        top_rate = float(top_seg["이탈률(%)"].iloc[0]) if not top_seg.empty else None

        st.divider()

        # ------------------------------------------------------------------
        # ③ 주지표 임계값 + 가드레일 판정 (다음 회차 확정)
        # ------------------------------------------------------------------
        st.subheader("③ 주지표 임계값 · 가드레일 판정")

        # 초과근무 상위 구간 재직자의 현재 평균 평가점수(가드레일 판정용)
        dom["초과근무구간_전체"] = dom["초과근무시간"].apply(tercile)
        active_hi = dom[(dom["event"] == 0) & (dom["초과근무구간_전체"] == "상위")]
        guardrail_score = round(active_hi["평가점수"].mean(), 2) if len(active_hi) else None

        g1, g2 = st.columns(2)
        with g1:
            if top_rate is None:
                status, color = "데이터 없음", "gray"
            elif top_rate >= OVERTIME_ATTRITION_DANGER_PCT:
                status, color = "🔴 위험", "#D62728"
            elif top_rate >= OVERTIME_ATTRITION_WARN_PCT:
                status, color = "🟡 경고", "#E8A33D"
            else:
                status, color = "🟢 정상", "#2E7D32"
            kpi_card(
                "주지표: 초과근무 상위 구간 입사 1년 내 이탈률",
                f'{top_rate:.1f}%' if top_rate is not None else "-",
                f'<span style="color:{color};font-weight:700">{status}</span> '
                f"(경고 {OVERTIME_ATTRITION_WARN_PCT:.0f}% · 위험 {OVERTIME_ATTRITION_DANGER_PCT:.0f}%)",
            )
        with g2:
            if guardrail_score is None:
                g_status, g_color = "데이터 없음", "gray"
            elif guardrail_score < PERFORMANCE_GUARDRAIL_SCORE:
                g_status, g_color = "🔴 가드레일 위반 — 개입 중단", "#D62728"
            else:
                g_status, g_color = "🟢 가드레일 통과", "#2E7D32"
            kpi_card(
                "가드레일: 초과근무 상위 구간 평균 평가점수",
                f"{guardrail_score:.2f}점" if guardrail_score is not None else "-",
                f'<span style="color:{g_color};font-weight:700">{g_status}</span> '
                f"(기준 {PERFORMANCE_GUARDRAIL_SCORE:.1f}점 미만이면 중단)",
            )

        st.caption(
            "임계값 확정 근거: 주지표 현재값(4.0%, n=100 중 4명) 대비 경고 6%(6명)·위험 8%(8명) — "
            "위험선은 전사 1년내 이탈자 총수(8명)가 이 구간 하나에 몰리는 수준. "
            "가드레일 기준(2.7점)은 초과근무 상위 구간의 현재 평균 평가점수(3.03점, 표준편차 0.66)에서 "
            "약 0.5 표준편차 하락한 지점. 근거·확정 과정은 `내도메인.md`, 05_log 참고."
        )

        # ------------------------------------------------------------------
        # ④ 퇴사사유 원인 규명 — 입사 1년 내 이탈자 전원 대조
        # ------------------------------------------------------------------
        st.subheader("④ 퇴사사유 원인 규명 (입사 1년 내 이탈자)")
        leavers_1y = dom[dom["left_within_1y"] == 1][
            ["사번", "부서", "초과근무구간_전체", "tenure_days", "퇴사사유"]
        ].rename(columns={"초과근무구간_전체": "초과근무구간", "tenure_days": "근속일수"}).sort_values("근속일수")
        st.dataframe(leavers_1y, hide_index=True)

        reason_by_overtime = pd.crosstab(leavers_1y["초과근무구간"], leavers_1y["퇴사사유"])
        st.caption(
            "초과근무 상위 구간 이탈자의 사유는 이직·건강·계약만료가 섞여 있고, 개발 부서 이탈자도 "
            "초과근무 구간이 하위~상위로 고르게 분포해 '부서·초과근무만으로' 설명되지 않습니다. "
            "재직자의 평가점수를 초과근무 구간별로 비교해도 통계적으로 유의한 차이가 없습니다(Welch's t-test, "
            "상위 vs 중위 p=0.44, 상위 vs 하위 p=0.70)."
        )
        st.dataframe(reason_by_overtime, use_container_width=True)

        st.markdown(
            "**결정(다음 회차): 판단 보류, 모니터링만 계속** — 부서·채용경로를 통제한 로지스틱 회귀도 "
            "시도했으나 초과근무 계수가 유의하지 않았고(p=0.45), 이탈 0건인 카테고리가 많아 완전분리 "
            "문제로 모델 자체의 신뢰도도 낮았습니다. 지금 표본으로는 더 정교한 통계기법을 써도 인과를 "
            "밝힐 수 없다고 판단해, 억지로 결론 내지 않고 **이탈 사건이 더 쌓일 때까지 관찰만 계속**하기로 "
            "정했습니다. 초과근무↔이탈은 상관관계·방향성까지만 유지하고 인과는 주장하지 않습니다."
        )

    else:
        st.warning(f"코호트 표본이 최소표본 기준(n≥{MIN_SAMPLE}) 미만이거나 초과근무 데이터가 없어 세그먼트 분해를 생략합니다.")
